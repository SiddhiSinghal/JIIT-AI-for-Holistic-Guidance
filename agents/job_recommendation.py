# job_recommendation.py
import pickle
import pandas as pd
from pymongo import MongoClient
from flask import session
import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Get the URI from .env file or Render environment
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["holistic_guidance"]
users_collection = db["users"]

# === Grade to numeric mapping ===
GRADE_TO_MARKS = {
    "A+": 100, "A": 90, "B+": 80, "B": 70,
    "C+": 60, "C": 50, "D": 40, "F": 0
}

# === Load model + encoder ===
def load_model_and_encoder():
    with open("agents/job_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open("agents/label_encoder.pkl", "rb") as f:
        encoder = pickle.load(f)
    return model, encoder


# === Extract marks from stored marksheets ===
def get_subject_marks_from_mongo(username):
    """
    Fetch the latest marksheet data for the logged-in user
    and compute subject-wise numeric scores.
    """

    user = users_collection.find_one({"username": username})
    if not user or "marksheets" not in user or len(user["marksheets"]) == 0:
        return None

    # Get latest uploaded marksheet
    latest = user["marksheets"][-1]

    # Map of subject keywords to model feature names
    subject_map = {
        "dsa": ["data structures", "dsa"],
        "dbms": ["dbms", "database"],
        "os": ["operating system", "os"],
        "cn": ["computer networks", "network"],
        "math": ["math", "applied mathematics"],
        "aptitude": ["aptitude", "reasoning", "statistics"],
        "comm": ["communication", "english", "writing"],
        "problem_solving": ["problem", "logic"],
        "creative": ["creative", "design", "innovation"],
        "hackathons": ["project", "hackathon", "workshop"]
    }

    # Default marks (0 for missing)
    marks = {k: 0 for k in subject_map.keys()}

    # Loop over subjects and map grades
    for subj in latest.get("subjects", []):
        name = subj["subject"].lower()
        grade = subj["grade"].upper()
        score = GRADE_TO_MARKS.get(grade, 0)

        for key, keywords in subject_map.items():
            if any(word in name for word in keywords):
                # Take the max grade if multiple subjects fit one category
                marks[key] = max(marks[key], score)

    return marks


# === Recommend jobs ===
def recommend_jobs(username):
    model, encoder = load_model_and_encoder()
    marks = get_subject_marks_from_mongo(username)

    if not marks:
        return ["No marksheet data found! Please upload your grade sheet."]

    # Build features list in correct order
    features = [
        marks["dsa"], marks["dbms"], marks["os"],
        marks["cn"], marks["math"], marks["aptitude"],
        marks["comm"], marks["problem_solving"],
        marks["creative"], marks["hackathons"]
    ]

    # Convert to DataFrame to match training features
    columns = ["DSA", "DBMS", "OS", "CN", "Mathmetics", "Aptitute",
               "Comm", "Problem Solving", "Creative", "Hackathons"]

    features_df = pd.DataFrame([features], columns=columns)

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features_df)[0]
        top_3_indices = probabilities.argsort()[-3:][::-1]
        top_3_jobs = encoder.inverse_transform(top_3_indices).tolist()
    else:
        pred = model.predict(features_df)
        top_3_jobs = encoder.inverse_transform(pred).tolist()

    return top_3_jobs

from markupsafe import Markup

def get_job_recommendation_message(username):
    """
    Returns a well-formatted HTML message showing top job roles for the user.
    """
    jobs = recommend_jobs(username)

    # ⚠️ Handle case where marksheet or model data is missing
    if not jobs or "marksheet" in jobs[0].lower():
        return Markup("""
        <div style='padding:15px;background:#fff8e1;border-left:5px solid #ffc107;
                    border-radius:10px;margin-bottom:10px;'>
            ⚠️ <b>Upload Required:</b><br>
            I couldn't find your marksheet data.<br>
            Please upload it in your <b>Profile section</b> so I can analyze your scores and
            recommend the best career paths for you! 📄✨
        </div>
        """)

    # ✅ Nicely formatted job recommendation block
    html = f"""
    <div style='padding:15px;background:#f1f8ff;border-left:6px solid #007bff;
                border-radius:12px;margin-bottom:15px;'>
        <h4 style='color:#007bff;margin-bottom:8px;'>💼 Based on your academic performance,</h4>
        <p style='color:#333;font-size:15px;margin-bottom:12px;'>
            Here are the <b>Top Job Roles</b> that align with your skills and subject strengths:
        </p>
    """

    # Add each job role as a card
    for i, job in enumerate(jobs, start=1):
        html += f"""
        <div style='padding:12px;margin:10px 0;background:white;
                    border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,0.1);'>
            <b style='color:#212529;'>{i}. {job}</b><br>
            <span style='color:#555;'>🧭 Explore further:</span><br>
            <a href='/chat?mode=career&role={job}' target='_blank'
               style='color:#007bff;text-decoration:none;font-size:14px;'>
               🔹 Career Info</a> |
            <a href='/chat?mode=roadmap&role={job}' target='_blank'
               style='color:#28a745;text-decoration:none;font-size:14px;'>
               🚀 Roadmap
            </a>
        </div>
        """

    html += """
        <p style='margin-top:15px;color:#444;font-size:14px;'>
            🌟 Stay consistent — focus on the skills linked to these roles to build a strong career foundation.
        </p>
    </div>
    """

    return Markup(html)
