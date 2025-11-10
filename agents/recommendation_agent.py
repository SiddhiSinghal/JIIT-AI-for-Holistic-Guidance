import pandas as pd
from pymongo import MongoClient
from difflib import SequenceMatcher
from utils import ai_utils
from utils.skills import SKILL_LABELS
import os
from dotenv import load_dotenv
from pymongo import MongoClient
# Load environment variables
load_dotenv()

# Get the URI from .env file or Render environment
MONGO_URI = os.getenv("MONGO_URI")
# --------------------------------------------------
# 1. FETCH GRADES FROM MONGODB
# --------------------------------------------------
def fetch_user_marks(username: str):
    """Fetch all marksheets for a user from MongoDB."""
    try:
        client = MongoClient(MONGO_URI)
        db = client["holistic_guidance"]
        users_collection = db["users"]

        user = users_collection.find_one({"username": username})
        if user and "marksheets" in user:
            return user["marksheets"]
        return []
    except Exception as e:
        print(f"⚠️ Error fetching marksheets: {e}")
        return []


# --------------------------------------------------
# 2. MAP SUBJECT NAMES TO CODES
# --------------------------------------------------
def map_subject_name_to_code(subject_name: str, subjects_df: pd.DataFrame) -> str:
    """Fuzzy match subject names from PDFs to subject codes."""
    if not subject_name:
        return None

    subject_clean = subject_name.strip().upper()
    exact_match = subjects_df[subjects_df["Subject Name"].str.upper() == subject_clean]
    if not exact_match.empty:
        return exact_match.iloc[0]["Subject Code"]

    best_match, best_ratio = None, 0.0
    for _, row in subjects_df.iterrows():
        df_name = str(row["Subject Name"]).upper()
        ratio = SequenceMatcher(None, subject_clean, df_name).ratio()
        if ratio > best_ratio and ratio >= 0.7:
            best_ratio = ratio
            best_match = row["Subject Code"]
    return best_match


# --------------------------------------------------
# 3. BUILD GRADE DICTIONARY
# --------------------------------------------------
def build_grades_dict(username: str, subjects_df: pd.DataFrame) -> dict:
    """Combine all marksheets into one dict of {subject_code: grade}."""
    marksheets = fetch_user_marks(username)
    grades_dict = {}

    if not marksheets:
        print(f"⚠️ No marksheets found for {username}")
        return {}

    print(f"📘 Processing {len(marksheets)} marksheet(s) for {username}")

    for sheet in marksheets:
        for subj in sheet.get("subjects", []):
            subject_name = subj.get("subject", "")
            grade = subj.get("grade", "")
            subject_code = map_subject_name_to_code(subject_name, subjects_df)
            if subject_code:
                grades_dict[subject_code] = grade
            else:
                print(f"⚠️ Could not match: {subject_name}")

    print(f"✅ Total mapped subjects: {len(grades_dict)}")
    return grades_dict


# --------------------------------------------------
# 4. GENERATE SUBJECT RECOMMENDATIONS
# --------------------------------------------------
def generate_subject_recommendations(username: str, subjects_xlsx_path: str, next_sem: int):
    """Generate next semester subject recommendations based on user's marks."""
    subjects_df = pd.read_excel(subjects_xlsx_path)
    subjects_df.columns = [c.strip() for c in subjects_df.columns]

    grades_dict = build_grades_dict(username, subjects_df)
    if not grades_dict:
        return "⚠️ No grades found. Please upload your marksheets first."

    skill_profile = ai_utils.build_student_skill_profile(
        grades_dict, subjects_df, ai_utils.map_subject_to_skills
    )

    local_model = ai_utils.LocalPredictionModel()
    next_df = subjects_df[
        (subjects_df["Semester"] == next_sem) &
        (subjects_df["Type"].isin(["E", "OC"]))
    ]

    results = []
    for _, row in next_df.iterrows():
        subj = row["Subject Name"]
        desc = row.get("Description", "")
        basket = row["Code"]

        strength_score = local_model.calculate_strength_score(
            grades_dict, subj, desc, subjects_df
        )
        try:
            market_score_100 = ai_utils.get_subject_market_score(subj, desc)
        except Exception:
            market_score_100 = 60.0

        combined_score = ai_utils.compute_combined_recommendation_score(
            strength_score, market_score_100 / 10, 0.6, 0.4
        )

        results.append({
            "Basket": basket,
            "Subject": subj,
            "Strength": round(strength_score, 2),
            "Market": round(market_score_100, 2),
            "Final Score": round(combined_score, 2)
        })

    df = pd.DataFrame(results).sort_values(["Basket", "Final Score"], ascending=[True, False])
    print(df)
    return df


# --------------------------------------------------
# 5. FORMAT OUTPUT FOR CHAT DISPLAY
# --------------------------------------------------
def format_recommendation_html(df: pd.DataFrame, next_sem: int) -> str:
    """Format DataFrame into clean HTML for chat display."""
    if df.empty:
        return "⚠️ No recommendations available."

    html = f"<b>📘 Recommended Electives for Semester {next_sem}</b><br><br>"
    for basket, grp in df.groupby("Basket"):
        html += f"<b>🧺 Basket {basket}</b><br>"
        for _, row in grp.iterrows():
            html += (
                f"• <b>{row['Subject']}</b><br>"
                f"&nbsp;&nbsp;💪 Strength: {row['Strength']} | 📈 Market: {row['Market']} | 🧮 Score: {row['Final Score']}<br>"
            )
        html += "<hr>"
    return html


# --------------------------------------------------
# 6. MAIN RUNNER (for testing)
# --------------------------------------------------
def run_recommendation_agent(username: str, subjects_xlsx_path="data/subjects.xlsx", next_sem=6):
    """Run recommendation agent and return formatted HTML for chat."""
    df = generate_subject_recommendations(username, subjects_xlsx_path, next_sem)

    # If something went wrong, return simple message
    if isinstance(df, str):
        return df

    # ✅ Convert DataFrame to nice HTML (no console printing)
    html = format_recommendation_html(df, next_sem)
    return html


# Example CLI run
if __name__ == "__main__":
    run_recommendation_agent("ss", "data/subjects.xlsx", 6)
