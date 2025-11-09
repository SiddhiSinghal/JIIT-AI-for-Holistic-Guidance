from flask import Flask, render_template, request, redirect, url_for, session, flash
from db_adapter import MockMongoClient as MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
import re
import orchestrator_cli
from summer_project.rag_chain import get_mental_health_response
from markupsafe import Markup
import json
import random
from datetime import datetime

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

client = MongoClient("mock://localhost:27017/")
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
    if "user" in session:
        return render_template("home.html", user=session["user"])
    else:
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


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]

    # Ensure user document exists
    user_data = users_collection.find_one({"username": username})
    if not user_data:
        users_collection.insert_one({
            "username": username,
            "marksheets": [],
            "assessments": []
        })
        user_data = {"username": username, "marksheets": [], "assessments": []}

    assessments = user_data.get("assessments", [])

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("⚠️ No file selected!")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("⚠️ Please upload a valid PDF file!")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        print(f"📄 File saved to: {filepath}")

        try:
            extracted_data = extract_marks_from_pdf(filepath)
            print("📊 Extracted Data:", extracted_data)

            if not extracted_data or not extracted_data.get("subjects"):
                flash("⚠️ Could not extract valid marks. Please upload a proper marksheet.")
                return redirect(request.url)

            # Manually update user_data for mock DB
            new_marksheet = {
                "semester": extracted_data.get("semester", "Unknown"),
                "branch": extracted_data.get("branch", "CSE"),
                "sgpa": extracted_data.get("sgpa", "N/A"),
                "cgpa": extracted_data.get("cgpa", "N/A"),
                "subjects": extracted_data.get("subjects", [])
            }

            # Add new entry to marksheets
            user_data.setdefault("marksheets", []).append(new_marksheet)

            # Update the collection
            users_collection.update_one({"username": username}, {"$set": user_data})

            flash("✅ Marksheet uploaded and processed successfully!")

            # ✅ Render updated data directly
            return render_template(
                "profile.html",
                user_data=user_data,
                assessments=user_data.get("assessments", []),
                user=username
            )

        except Exception as e:
            print("❌ Error during PDF processing:", e)
            flash(f"❌ Error: {e}")
            return redirect(request.url)

    # GET → show existing data
    user_data = users_collection.find_one({"username": username}, {"_id": 0}) or {"marksheets": [], "assessments": []}
    print(f"👤 Loaded User Data for {username}: {user_data}")
    assessments = user_data.get("assessments", [])

    return render_template("profile.html", user_data=user_data, assessments=assessments, user=username)


# ==================== UNIFIED CHAT (CAREER + MENTAL + TESTS) ====================
from markupsafe import Markup
@app.route("/chat", methods=["GET", "POST"])
def unified_chat():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]

    # ------------------------ GET (start chat) ------------------------
    if request.method == "GET":
        session["chat_history"] = []
        session.pop("test_intent", None)
        
        mode = request.args.get("mode", "")
        
        welcome_messages = {
            "career": """
                <div style='padding:15px;background:#e8f4fd;border-left:5px solid #2196f3;border-radius:10px;'>
                  <b>💼 Career Guidance Assistant</b><br><br>
                  Welcome! I'm here to help you explore career opportunities, understand different professions, 
                  and guide you toward the right career path based on your skills and interests.<br><br>
                  Ask me about career options, job roles, industry trends, or career advice!
                </div>
            """,
            "mental_health": """
                <div style='padding:15px;background:#fef5e7;border-left:5px solid #f39c12;border-radius:10px;'>
                  <b>❤️ Mental Health Support</b><br><br>
                  I'm here to provide a supportive space for you. Whether you're feeling stressed, anxious, 
                  or just need someone to talk to, I'm here to listen and offer guidance.<br><br>
                  Remember: Your mental health matters, and it's okay to ask for help.
                </div>
            """,
            "linkedin": """
                <div style='padding:15px;background:#e3f2fd;border-left:5px solid #0077b5;border-radius:10px;'>
                  <b>✍️ LinkedIn Post Generator</b><br><br>
                  Let's create engaging LinkedIn content! I can help you craft professional posts about your 
                  achievements, insights, industry trends, or any topic you'd like to share with your network.<br><br>
                  Tell me what you'd like to write about, and I'll generate a polished LinkedIn post for you!
                </div>
            """,
            "jobs": """
                <div style='padding:15px;background:#e8f5e9;border-left:5px solid #4caf50;border-radius:10px;'>
                  <b>💼 Job Recommendations</b><br><br>
                  I'll analyze your profile and suggest job roles that match your skills and interests. 
                  Get personalized job recommendations based on your academic performance and strengths.<br><br>
                  Ask me for job suggestions or tell me about your career interests!
                </div>
            """,
            "mooc": """
                <div style='padding:15px;background:#fff3e0;border-left:5px solid #ff9800;border-radius:10px;'>
                  <b>📚 MOOC Course Recommendations</b><br><br>
                  Looking to upskill? I can help you find the best online courses from platforms like 
                  Coursera, edX, Udemy, and more, tailored to your interests and career goals.<br><br>
                  Tell me what skills you want to learn!
                </div>
            """,
            "electives": """
                <div style='padding:15px;background:#f3e5f5;border-left:5px solid #9c27b0;border-radius:10px;'>
                  <b>🎓 Elective Recommendations</b><br><br>
                  Choosing the right electives can shape your career path! I'll help you select subjects 
                  that align with your interests, strengths, and future goals.<br><br>
                  Tell me about your semester or interests, and I'll suggest the best electives!
                </div>
            """,
            "market_score": """
                <div style='padding:15px;background:#fce4ec;border-left:5px solid #e91e63;border-radius:10px;'>
                  <b>📊 Market Score Analysis</b><br><br>
                  Understand the market demand for different subjects and skills! I'll provide insights 
                  into which areas are trending and have strong job prospects.<br><br>
                  Ask me about market demand for any subject or technology!
                </div>
            """
        }
        
        chat_type_names = {
            "career": "Career Guidance",
            "mental_health": "Mental Health",
            "linkedin": "LinkedIn Post Generator",
            "jobs": "Job Recommendations",
            "mooc": "MOOC Courses",
            "electives": "Elective Suggestions",
            "market_score": "Market Analysis"
        }
        
        welcome_message = welcome_messages.get(mode, """
            <div style='padding:15px;background:#f1f8ff;border-left:5px solid #007bff;border-radius:10px;'>
              <b>👋 Welcome to your holistic guidance companion!</b><br><br>
              This is your personal space for support through every part of your student journey.
              Whether it's your studies, career, health, or personal growth, I'm here to guide you 
              toward clarity, confidence, and progress.<br><br>
              What would you like to begin with today? 💡
            </div>
        """)
        
        chat_type = chat_type_names.get(mode, "Unified")
        
        session["chat_history"] = [{"sender": "ai", "text": welcome_message, "html": True}]
        return render_template("chat.html", user=username, chat_history=session["chat_history"], chat_type=chat_type)


    # ------------------------ POST (handle message) ------------------------
    chat_history = session.get("chat_history", [])
    user_message = request.form["prompt"].strip()
    chat_history.append({"sender": "user", "text": user_message})

    ai_reply = None
    last_ai_text = chat_history[-2]["text"].lower() if len(chat_history) > 1 and chat_history[-2]["sender"] == "ai" else ""

    try:
        # ✅ Prevent repeating the same test or action
        if "opening your" in last_ai_text and not any(
            word in user_message.lower() for word in ["aptitude", "communication", "creativity", "coding"]
        ):
            ai_reply = orchestrator_cli.orchestrate(user_message, username=username, last_user_message=user_message)

        # 🔹 Detect emotional content (mental health)
        elif any(word in user_message.lower() for word in ["tired", "stressed", "sad", "depressed", "hopeless", "anxious", "lonely", "pressure"]):
            ai_reply = get_mental_health_response(user_message)

        # 🔹 Detect test-related intent (with regex, so it’s not over-sensitive)
        elif re.search(r"\b(take|start|begin|attempt|give).*\btest\b", user_message.lower()):
            test_map = {
                "aptitude": "/aptitude_test",
                "communication": "/communication_test",
                "creativity": "/creativity_test",
                "coding": "/coding_test"
            }
            selected_test = None
            for key in test_map.keys():
                if key in user_message.lower():
                    selected_test = key
                    break

            if not selected_test:
                ai_reply = {
                    "sender": "ai",
                    "text": """
                    Which test would you like to take? 💡<br>
                    You can choose one of the following:<br>
                    👉 Aptitude<br>
                    👉 Communication<br>
                    👉 Creativity<br>
                    👉 Coding
                    """,
                    "html": True
                }
                session["test_intent"] = True
            else:
                test_url = test_map[selected_test]
                ai_reply = {
                    "sender": "ai",
                    "html": True,
                    "text": f"""
                    <div style='padding:15px;background:#e3f2fd;border-left:5px solid #2196f3;border-radius:8px;'>
                      🚀 Ready to begin your <b>{selected_test.capitalize()} Test</b>?<br><br>
                      <a href='{test_url}' target='_blank' rel='noopener noreferrer'>
                        <button style='background:#007bff;color:white;border:none;padding:8px 16px;border-radius:5px;cursor:pointer;'>
                          Start Test
                        </button>
                      </a>
                    </div>
                    """
                }
                session["test_intent"] = False

        # 🔹 If user had previously said “start test” but now gives the type name only
        elif session.get("test_intent") and any(k in user_message.lower() for k in ["aptitude", "communication", "creativity", "coding"]):
            test_map = {
                "aptitude": "/aptitude_test",
                "communication": "/communication_test",
                "creativity": "/creativity_test",
                "coding": "/coding_test"
            }
            for key, url in test_map.items():
                if key in user_message.lower():
                    test_url = url
                    ai_reply = {
                        "sender": "ai",
                        "html": True,
                        "text": f"""
                        <div style='padding:15px;background:#e3f2fd;border-left:5px solid #2196f3;border-radius:8px;'>
                        🚀 Ready to begin your <b>{key.capitalize()} Test</b>?<br><br>
                        <a href='{test_url}' target='_blank' rel='noopener noreferrer'>
                        <button style='background:#007bff;color:white;border:none;padding:8px 16px;border-radius:5px;cursor:pointer;'>
                          Start Test
                        </button>
                        </a>
                        </div>
                        """
                    }

                    session["test_intent"] = False
                    break

        # 🔹 Otherwise, handle normally via orchestrator
        else:
            ai_reply = orchestrator_cli.orchestrate(user_message, username=username, last_user_message=user_message)
            session["test_intent"] = False

    except Exception as e:
        ai_reply = f"Sorry, there was an error: {e}"

    # ------------------------ Append AI reply ------------------------
    if isinstance(ai_reply, dict):
        chat_history.append(ai_reply)
    elif isinstance(ai_reply, Markup):
        chat_history.append({"sender": "ai", "text": str(ai_reply), "html": True})
    else:
        chat_history.append({"sender": "ai", "text": str(ai_reply), "html": False})

    # 🌿 Mid-conversation encouragement every 5 user messages
    user_msgs = [m for m in chat_history if isinstance(m, dict) and m.get("sender") == "user"]
    if len(user_msgs) % 5 == 0:
        mid_message = """
        <div style='padding:10px;background:#e8f5e9;border-left:4px solid #43a047;border-radius:8px;'>
          You're doing great! 🌱<br>
          Would you like to continue chatting or explore a test or career advice?
        </div>
        """
        chat_history.append({"sender": "ai", "text": mid_message, "html": True})

    # ✅ Always reset state before returning
    session["chat_history"] = chat_history[-12:]
    session.pop("selected_questions", None)
    session.pop("question", None)
    return render_template("chat.html", user=username, chat_history=session["chat_history"], chat_type="Unified")

# ==================== TEST ROUTES ====================

# Load aptitude questions from JSON
QUESTIONS_FILE = "aptitude_questions.json"

def load_questions():
    with open(QUESTIONS_FILE, "r") as f:
        return json.load(f)


@app.route("/aptitude_test", methods=["GET", "POST"])
def aptitude_test():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]

    if request.method == "POST":
        selected_questions = session.get("selected_questions", [])
        user_answers = request.form

        correct_answers = {q["id"]: q["answer"] for q in selected_questions}
        score = sum(
            10 for q_id, correct in correct_answers.items()
            if user_answers.get(q_id, "").strip().lower() == correct.strip().lower()
        )

        # Save to MongoDB
        users_collection.update_one(
            {"username": username},
            {"$push": {"assessments": {
                "type": "Aptitude Test",
                "score": score,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }}}
        )


        return render_template("test_done.html", test="Aptitude", score=score)

    # GET → show random 10 questions
    questions = load_questions()
    selected_questions = random.sample(questions, 10)
    session["selected_questions"] = selected_questions
    return render_template("aptitude_test.html", questions=selected_questions)


@app.route("/communication_test", methods=["GET", "POST"])
def communication_test():
    if "user" not in session:
        return redirect(url_for("login"))
    username = session["user"]

    if request.method == "POST":
        text = request.form.get("response", "")
        score = min(10, len(text.split()) // 20)  # simplistic scoring

        users_collection.update_one(
            {"username": username},
            {"$push": {"assessments": {
                "type": "Communication Test",
                "score": score,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }}}
        )

        return render_template("test_done.html", test="Communication", score=score)

    return render_template("communication_test.html")


@app.route("/creativity_test", methods=["GET", "POST"])
def creativity_test():
    if "user" not in session:
        return redirect(url_for("login"))
    username = session["user"]

    PROMPTS = [
        "Write a story about a world where dreams come true.",
        "Describe a day in the life of a time traveler.",
        "A mysterious door appears in your house. What happens next?",
        "You wake up with a superpower. What is it and how do you use it?"
    ]

    if request.method == "POST":
        story = request.form.get("story", "")
        creativity = min(10, len(set(story.split())) // 8)
        coherence = min(10, len(story.split(".")) // 3)
        score = (creativity + coherence) / 2

        users_collection.update_one(
            {"username": username},
            {"$push": {
                "assessments": {
                    "type": "Creativity Test",
                    "score": score,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }}
        )

        return render_template("test_done.html", test="Creativity", score=score)

    prompt = random.choice(PROMPTS)
    return render_template("creativity_test.html", prompt=prompt)


@app.route("/coding_test", methods=["GET", "POST"])
def coding_test():
    if "user" not in session:
        return redirect(url_for("login"))
    username = session["user"]

    questions = [
        "Reverse a string.",
        "Check if a number is a prime number.",
        "Find the factorial of a number.",
        "Find the largest element in an array.",
        "Check if a number is a palindrome."
    ]

    expected_outputs = {
        "Reverse a string.": "gnirts",
        "Check if a number is a prime number.": "Prime",
        "Find the factorial of a number.": "120",
        "Find the largest element in an array.": "9",
        "Check if a number is a palindrome.": "Palindrome"
    }

    if "question" not in session:
        session["question"] = random.choice(questions)
    question = session["question"]
    output, marks = None, 0

    if request.method == "POST":
        code = request.form["code"]
        custom_input = request.form.get("custom_input", "")

        try:
            with open("user_code.cpp", "w") as f:
                f.write(code)
            compile_result = os.system("g++ user_code.cpp -o user_code.out")

            if compile_result == 0:
                stream = os.popen(f"./user_code.out")
                output = stream.read().strip()
                expected = expected_outputs.get(question, "")
                marks = 100 if output.strip() == expected else 50
            else:
                output = "❌ Compilation error"
        except Exception as e:
            output = str(e)

        users_collection.update_one(
            {"username": username},
            {"$push": {
                "assessments": {
                    "type": "Coding Test",
                    "score": marks,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }}
        )

        return render_template("test_done.html", test="Coding", score=marks)

    return render_template("coding_test.html", question=question)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
