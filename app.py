from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
import re
import orchestrator_cli
from summer_project.rag_chain import get_mental_health_response
from markupsafe import Markup


# ==== Import from utils for later integration ====
from utils.ai_utils import (
    map_subject_to_skills, get_subject_market_score,
    build_student_skill_profile,
    score_subject_for_student,
    GRADE_MAP,
    compute_subject_score,
    compute_combined_recommendation_score,
    compute_local_strength_score,
)
from utils.skills import SKILL_LABELS


# ==================== FLASK & MONGO SETUP ====================
app = Flask(__name__)
app.secret_key = "super_secret_key"

client = MongoClient("mongodb://localhost:27017/")
db = client["holistic_guidance"]
users_collection = db["users"]

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"pdf"}


# ==================== HELPERS ====================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_marks_from_pdf(filepath):
    """Extracts subject and grade pairs (and optional sem, branch, sgpa, cgpa)"""
    doc = fitz.open(filepath)
    text = "".join([page.get_text("text") for page in doc])
    text = re.sub(r'\s+', ' ', text)

    data = {
        "semester": None,
        "branch": None,
        "sgpa": None,
        "cgpa": None,
        "subjects": []
    }

    branch_match = re.search(r"Program\s*\(Branch\)\s*[:\-]?\s*([A-Za-z\s&().]+)", text, re.IGNORECASE)
    if branch_match:
        data["branch"] = branch_match.group(1).strip()

    sem_match = re.search(r"Semester\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
    if sem_match:
        data["semester"] = sem_match.group(1)

    sgpa_match = re.search(r"Student\s*Sgpa\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
    cgpa_match = re.search(r"Student\s*Cgpa\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)

    if sgpa_match:
        data["sgpa"] = float(sgpa_match.group(1))
    if cgpa_match:
        data["cgpa"] = float(cgpa_match.group(1))

    pattern = re.compile(
        r"\d+\s+[A-Z0-9]+\s+([A-Za-z&\-/().\s]+?)\s+\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+([ABCOP][\+\-]?)\s+Pass",
        re.IGNORECASE
    )

    matches = pattern.findall(text)
    for match in matches:
        subject = match[0].strip().title()
        grade = match[1].strip().upper()
        data["subjects"].append({"subject": subject, "grade": grade})

    return data


# ==================== AUTH ROUTES ====================
@app.route("/")
def home():
    # If user is logged in, show a small dashboard with links
    if "user" in session:
        return render_template("home.html", user=session["user"])
    else:
        # If not logged in, show the welcome page with login/signup buttons
        return render_template("index.html")



@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if users_collection.find_one({"username": username}):
            flash("Username already exists! Please log in.")
            return redirect(url_for("login"))

        hashed_pw = generate_password_hash(password)
        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": hashed_pw,
            "marksheets": []
        })
        flash("Signup successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["user"] = username
            session["chat_history"] = []
            return redirect(url_for("unified_chat"))
        else:
            flash("Invalid credentials!")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.")
    return redirect(url_for("login"))


# ==================== PROFILE ROUTE ====================
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    user_data = users_collection.find_one({"username": username}, {"_id": 0})

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("⚠️ No file selected!")
            return redirect(request.url)

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            extracted_data = extract_marks_from_pdf(filepath)
            users_collection.update_one(
                {"username": username},
                {"$push": {"marksheets": {
                    "semester": extracted_data["semester"],
                    "branch": extracted_data["branch"],
                    "sgpa": extracted_data["sgpa"],
                    "cgpa": extracted_data["cgpa"],
                    "subjects": extracted_data["subjects"]
                }}}
            )
            flash("✅ Marksheet processed successfully!")
            return redirect(url_for("profile"))
        else:
            flash("❌ Please upload a valid PDF file!")

    user_data = users_collection.find_one({"username": username}, {"_id": 0})
    return render_template("profile.html", user_data=user_data, user=username)


# ==================== UNIFIED CHAT (CAREER + MENTAL) ====================
@app.route("/chat", methods=["GET", "POST"])
def unified_chat():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    chat_history = session.get("chat_history", [])

    if request.method == "POST":
        user_message = request.form["prompt"].strip()
        if not user_message:
            flash("⚠️ Please enter a message.")
            return redirect(url_for("unified_chat"))

        # 🧠 Add user message to chat history
        chat_history.append({"sender": "user", "text": user_message, "html": False})

        # 🔹 Detect if user seems emotionally low → redirect to mental health model
        stress_keywords = [
            "tired", "stressed", "sad", "depressed", "done",
            "fed up", "hopeless", "burnout", "anxious", "lonely"
        ]

        try:
            if any(word in user_message.lower() for word in stress_keywords):
                # 💬 Empathetic mental health response
                ai_reply = get_mental_health_response(user_message)

            else:
                # 🧭 Route to appropriate LLM or ML agent
                task_type = orchestrator_cli.classify_prompt(user_message)

                if task_type in orchestrator_cli.LLM_AGENTS:
                    ai_reply = orchestrator_cli.run_llm_agent(task_type, user_message)

                elif task_type in orchestrator_cli.NON_LLM_AGENTS:
                    ai_reply = orchestrator_cli.run_non_llm_agent(task_type, username=username)

                else:
                    ai_reply = (
                        "🤖 I'm here to help — could you tell me whether this is about your "
                        "<b>career</b> or <b>mental well-being</b>?"
                    )

        except Exception as e:
            ai_reply = f"⚠️ Sorry, there was an error: {str(e)}"

        # 💡 Append AI response (HTML allowed for skill charts, job lists, etc.)
        chat_history.append({"sender": "ai", "text": Markup(ai_reply), "html": True})

        # Save updated conversation
        session["chat_history"] = chat_history
        return redirect(url_for("unified_chat"))

    # Render chat template
    return render_template(
        "chat.html",
        user=username,
        chat_type="Unified",
        chat_history=chat_history
    )

if __name__ == "__main__":
    app.run(debug=True)
