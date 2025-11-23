import pandas as pd
from collections import defaultdict
from pymongo import MongoClient
from difflib import SequenceMatcher
import plotly.express as px
import os
from dotenv import load_dotenv

from utils import ai_utils
from utils.skills import SKILL_LABELS


# ===========================================
# 1️⃣ Connect to MongoDB Atlas
# ===========================================
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def fetch_grades_from_mongodb(username: str) -> list:
    """Fetch marksheets from MongoDB Atlas."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client["holistic_guidance"]
        user = db["users"].find_one({"username": username})
        if user and "marksheets" in user:
            return user["marksheets"]
    except Exception as e:
        print(f"⚠️ MongoDB Fetch Error: {e}")
    return []


# ===========================================
# 2️⃣ Subject Name → Code Mapper
# ===========================================
def map_subject_name_to_code(subject_name: str, subjects_df: pd.DataFrame) -> str:
    if not subject_name:
        return None

    subject_name_clean = subject_name.strip().upper()

    exact = subjects_df[subjects_df["Subject Name"].str.upper() == subject_name_clean]
    if not exact.empty:
        return exact.iloc[0]["Subject Code"]

    best_match, best_ratio = None, 0.0
    for _, row in subjects_df.iterrows():
        ratio = SequenceMatcher(None, subject_name_clean, str(row["Subject Name"]).upper()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = row["Subject Code"]

    return best_match if best_ratio >= 0.7 else None


# ===========================================
# 3️⃣ Convert Grades to Dict
# ===========================================
def convert_grades_to_dict(username: str, subjects_df: pd.DataFrame) -> dict:
    marksheets = fetch_grades_from_mongodb(username)
    grades_dict = {}

    if not marksheets:
        print("⚠️ No marksheets found for user:", username)
        return {}

    print(f"📚 Found {len(marksheets)} marksheet(s) for {username}")

    for marksheet in marksheets:
        for subj in marksheet.get("subjects", []):
            name = subj.get("subject", "").strip()
            grade = subj.get("grade", "").strip()
            if not name or not grade:
                continue

            subj_code = map_subject_name_to_code(name, subjects_df)
            if subj_code:
                grades_dict[subj_code] = grade
                print(f"  ✓ {name} → {subj_code} ({grade})")
            else:
                print(f"  ⚠ Could not match: {name}")

    return grades_dict


# ===========================================
# 4️⃣ Build Skill Profile
# ===========================================
def build_skill_profile(username: str, subjects_xlsx_path: str):
    subjects_df = pd.read_excel(subjects_xlsx_path)
    subjects_df.columns = [c.strip() for c in subjects_df.columns]

    grades_dict = convert_grades_to_dict(username, subjects_df)

    if not grades_dict:
        print("⚠️ No grades found to build profile.")
        return {}

    skill_profile = ai_utils.build_student_skill_profile(
        grades_dict, subjects_df, ai_utils.map_subject_to_skills
    )

    return skill_profile


# ===========================================
# 5️⃣ Return Plotly Graph HTML
# ===========================================
def plot_skill_profile(skill_profile):
    """Return Plotly graph HTML."""
    if not skill_profile:
        return "<p>No skills found to visualize.</p>"

    df = pd.DataFrame(list(skill_profile.items()), columns=["Skill", "Score"])
    df = df.sort_values("Score", ascending=False).head(15)

    fig = px.bar(
        df,
        x="Score",
        y="Skill",
        orientation="h",
        title="📊 Top 15 Skills",
        color="Score",
        color_continuous_scale="viridis"
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


# ===========================================
# 6️⃣ Main Runner
# ===========================================
def run_skill_profiler(username: str, subjects_xlsx_path: str):
    print("\n" + "=" * 60)
    print(f"🚀 Building Skill Profile for {username}")
    print("=" * 60)

    profile = build_skill_profile(username, subjects_xlsx_path)

    if not profile:
        return {
            "profile": {},
            "graph_html": "<p>⚠️ No skill data available to generate graph.</p>"
        }

    graph_html = plot_skill_profile(profile)

    print("=" * 60)
    return {"profile": profile, "graph_html": graph_html}
