from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, UserScores
from dotenv import load_dotenv
from openai import OpenAI
import os
from agents.job_recommendation import recommend_jobs

# Load .env
load_dotenv()

# Init OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///studentmarks.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from orchestrator import decide_and_call

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('home.html')

# ----------------- AUTH -----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid credentials")
    return render_template('login.html')


@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Signup successful. Login now!")
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# ----------------- DASHBOARD -----------------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)


# ----------------- SUBMIT SCORES -----------------
@app.route("/submit_scores", methods=["POST"])
@login_required
def submit_scores():
    # Collect user scores
    scores = {k: int(request.form[k]) for k in [
        "dsa","dbms","os","cn","math","aptitude","comm","problem_solving","creative","hackathons"
    ]}
    # Save scores
    user_score = UserScores(user_id=current_user.id, **scores)
    db.session.add(user_score)
    db.session.commit()

    # Get top 3 jobs (recommend_jobs takes no parameters)
    from agents.job_recommendation import recommend_jobs
    top_jobs = recommend_jobs()  # Must return a list: ["Software Engineer", "Data Scientist", "Network Engineer"]

    # Format nicely for HTML
    top_jobs_str = "<br>".join([f"{i+1}. {job}" for i, job in enumerate(top_jobs)])


    initial_message = f"Hello, {current_user.name} 👋<br>Based on your scores, here are your top 3 job recommendations:<br>{top_jobs_str}<br><br>You can now ask about any job or request a roadmap."

    # Render chat page and send initial message
    return render_template("chat.html", initial_message=initial_message, user=current_user)


# ----------------- CHAT ROUTE -----------------
@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        user_msg = request.json.get("message")
        user_scores = {}  # Or fetch from DB if you want personalized job recommendations
        response = decide_and_call(user_msg, user_scores=user_scores)  # removed user_name if not in orchestrator
        return jsonify({"reply": response['payload']})
    except Exception as e:
        print("Error in chat:", e)
        return jsonify({"reply": "Something went wrong."})

if __name__ == '__main__':
    app.run(debug=True)
