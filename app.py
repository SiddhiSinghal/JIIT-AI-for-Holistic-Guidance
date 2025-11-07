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
            flash(" Please upload a valid PDF file!")

    user_data = users_collection.find_one({"username": username}, {"_id": 0})
    return render_template("profile.html", user_data=user_data, user=username)


# ==================== UNIFIED CHAT (CAREER + MENTAL) ====================
from markupsafe import Markup

@app.route("/chat", methods=["GET", "POST"])
def unified_chat():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]

    # 💬 Always start a fresh chat when user opens this page
    if request.method == "GET":
        session["chat_history"] = []

        # 🩵 Initial welcome message
        welcome_message = """
        <div style='padding:15px;background:#f1f8ff;border-left:5px solid #007bff;border-radius:10px;'>
          <b> Hi there! Welcome to your Holistic Guidance Companion</b><br><br>
          This is your personal space for support through every part of your student journey.<br><br>
          Whether it’s your <b>studies </b>, <b>career </b>, <b>mental health </b>, or <b>personal growth </b>, 
          I’m here to guide you toward <b>clarity, confidence, and progress</b>.<br><br>
          <i>What would you like to begin with today?</i>
        </div>
        """

        # Store this as the first message
        session["chat_history"] = [{"sender": "ai", "text": welcome_message, "html": True}]

        return render_template(
            "chat.html",
            user=username,
            chat_history=session["chat_history"],
            chat_type="Unified"
        )

    # ========================
    # POST request → Handle message
    # ========================
    chat_history = session.get("chat_history", [])
    ai_reply = None

    if request.method == "POST":
        user_message = request.form["prompt"]
        chat_history.append({"sender": "user", "text": user_message})

        # 🔹 Emotion detection → switch to mental health mode
        stress_keywords = [
            "tired", "stressed", "sad", "depressed", "done", "fed up",
            "hopeless", "anxious", "burnout", "lonely", "pressure"
        ]

        try:
            if any(word in user_message.lower() for word in stress_keywords):
                ai_reply = get_mental_health_response(user_message)
            else:
                ai_reply = orchestrator_cli.orchestrate(
                    user_message, username=username, last_user_message=user_message
                )
        except Exception as e:
            ai_reply = f" Sorry, there was an error: {e}"

        # 🧩 Append AI response
        if isinstance(ai_reply, Markup):
            chat_history.append({"sender": "ai", "text": str(ai_reply), "html": True})
        else:
            chat_history.append({"sender": "ai", "text": str(ai_reply), "html": False})

        # 🌿 Add a mid-conversation encouragement every 5 user messages
        user_msgs = [m for m in chat_history if m["sender"] == "user"]
        if len(user_msgs) % 5 == 0:
            mid_message = """
            <div style='padding:10px;background:#e8f5e9;border-left:4px solid #43a047;border-radius:8px;'>
              I’m really enjoying our conversation!<br>
              Do you want to continue here, or explore another area like 
              <b>Studies </b>, <b>Career </b>, <b>Health </b>, or <b>Personal Growth </b>?
            </div>
            """
            chat_history.append({"sender": "ai", "text": mid_message, "html": True})

        # ✅ Keep chat small (avoid cookie overflow)
        session["chat_history"] = chat_history[-10:]

        # ⚡ Render directly
        return render_template(
            "chat.html",
            user=username,
            chat_history=chat_history,
            chat_type="Unified"
        )

if __name__ == "__main__":
    app.run(debug=True)
