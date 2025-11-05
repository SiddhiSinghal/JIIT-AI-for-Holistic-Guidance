from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os

# === Flask Setup ===
app = Flask(__name__)
app.secret_key = "super_secret_key"

# === MongoDB Setup ===
client = MongoClient("mongodb://localhost:27017/")
db = client["holistic_guidance"]
users_collection = db["users"]

# === Career Guidance Imports ===
import orchestrator_cli

# === Mental Health Import ===
from summer_project.rag_chain import get_mental_health_response


# ==================== AUTH ROUTES ====================

@app.route("/")
def home():
    if "user" in session:
        return render_template("index.html", user=session["user"])
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if users_collection.find_one({"username": username}):
            flash("Username already exists! Please log in.")
            return redirect(url_for("login"))

        hashed_pw = generate_password_hash(password)
        users_collection.insert_one({"username": username, "password": hashed_pw})
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
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials!")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))


# ==================== CHAT ROUTES ====================

@app.route("/career_chat", methods=["GET", "POST"])
def career_chat():
    """
    Career Chat route – handles LLM tasks including MOOC DeepSeek RAG queries.
    """
    if "user" not in session:
        return redirect(url_for("login"))

    result = None
    error = None

    if request.method == "POST":
        prompt = request.form["prompt"]
        task_type = orchestrator_cli.classify_prompt(prompt)

        try:
            if task_type in orchestrator_cli.LLM_AGENTS:
                result = orchestrator_cli.run_llm_agent(task_type, prompt)
            else:
                result = "❌ Unknown task type."
        except Exception as e:
            error = f"⚠️ Error: {str(e)}"

    return render_template(
        "career_chat.html",
        user=session["user"],
        result=result,
        error=error
    )


@app.route("/mental_chat", methods=["GET", "POST"])
def mental_chat():
    if "user" not in session:
        return redirect(url_for("login"))

    result = None
    if request.method == "POST":
        prompt = request.form["prompt"]
        result = get_mental_health_response(prompt)

    return render_template("mental_chat.html", user=session["user"], result=result)


# ==================== FILE UPLOAD (optional, for MOOC PDF change) ====================

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "user" not in session:
        return redirect(url_for("login"))

    uploaded_file = request.files.get("pdf_file")
    if uploaded_file and uploaded_file.filename.endswith(".pdf"):
        save_path = os.path.join(os.getcwd(), uploaded_file.filename)
        uploaded_file.save(save_path)
        os.environ["PDF_PATH"] = save_path
        flash(f"PDF uploaded successfully: {uploaded_file.filename}")
    else:
        flash("Please upload a valid PDF file.")
    return redirect(url_for("career_chat"))


# ==================== MAIN ====================

if __name__ == "__main__":
    app.run(debug=True)
