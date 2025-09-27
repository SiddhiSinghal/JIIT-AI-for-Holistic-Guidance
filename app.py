from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, UserScores
from orchestrator import decide_and_call
from dotenv import load_dotenv
from openai import OpenAI
import os

# Load .env
load_dotenv()

# Init OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://siddhi:yourpassword@localhost:5432/ai_agents"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            return redirect(url_for("signup"))

        new_user = User(name=name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Signup successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password!", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        scores = UserScores(
            user_id=current_user.id,
            dsa=request.form["dsa"],
            dbms=request.form["dbms"],
            os=request.form["os"],
            cn=request.form["cn"],
            math=request.form["math"],
            aptitude=request.form["aptitude"],
            comm=request.form["comm"],
            problem_solving=request.form["problem_solving"],
            creative=request.form["creative"],
            hackathons=request.form["hackathons"],
        )
        db.session.add(scores)
        db.session.commit()
        flash("Scores saved successfully!", "success")
        return redirect(url_for("chat"))

    return render_template("dashboard.html", user=current_user)


@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    if request.method == "POST":
        data = request.get_json()
        user_message = data.get("message")

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful career guidance assistant."},
                    {"role": "user", "content": user_message}
                ]
            )
            bot_reply = response.choices[0].message.content
            return jsonify({"reply": bot_reply})
        except Exception as e:
            return jsonify({"error": str(e)})
    
    return render_template("chat.html", user=current_user)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
