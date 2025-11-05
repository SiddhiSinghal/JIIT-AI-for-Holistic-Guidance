# agents/skill_profiler_agent.py

import pandas as pd
import plotly.express as px
from collections import defaultdict
from pymongo import MongoClient
from difflib import SequenceMatcher

from utils import ai_utils
from utils.skills import SKILL_LABELS

# --------------------------
# 1. Load Grades from Various Sources
# --------------------------
def load_grades_from_txt(file_path: str) -> dict:
    """Load grades from a text file (legacy method)."""
    grades = {}
    with open(file_path, "r") as f:
        for line in f:
            if ":" in line:
                subj, grade = line.strip().split(":")
                grades[subj.strip()] = grade.strip()
    return grades

def fetch_grades_from_mongodb(username: str) -> list:
    """
    Fetch all marksheets from MongoDB for a given username.
    Returns list of marksheets with subjects and grades extracted from PDF.
    """
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["holistic_guidance"]
        users_collection = db["users"]
        
        user = users_collection.find_one({"username": username})
        if user and "marksheets" in user:
            return user["marksheets"]
    except Exception as e:
        print(f"⚠️ Error fetching from MongoDB: {e}")
    return []

def map_subject_name_to_code(subject_name: str, subjects_df: pd.DataFrame) -> str:
    """
    Map a subject name (from PDF) to subject code (from subjects.xlsx).
    Uses fuzzy matching to handle variations in naming.
    """
    if subject_name is None or subject_name.strip() == "":
        return None
    
    # Normalize subject name for matching
    subject_name_clean = subject_name.strip().upper()
    
    # Try exact match first
    exact_match = subjects_df[subjects_df["Subject Name"].str.upper() == subject_name_clean]
    if not exact_match.empty:
        return exact_match.iloc[0]["Subject Code"]
    
    # Try fuzzy matching
    best_match = None
    best_ratio = 0.0
    threshold = 0.7  # Minimum similarity ratio
    
    for _, row in subjects_df.iterrows():
        subject_name_in_df = str(row["Subject Name"]).upper()
        ratio = SequenceMatcher(None, subject_name_clean, subject_name_in_df).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = row["Subject Code"]
    
    return best_match

def convert_pdf_grades_to_dict(username: str, subjects_df: pd.DataFrame) -> dict:
    """
    Convert PDF-extracted grades (subject names) to grades dict (subject codes).
    Fetches all marksheets from MongoDB and maps subject names to codes.
    
    Returns:
        dict: {subject_code: grade} format
    """
    marksheets = fetch_grades_from_mongodb(username)
    grades_dict = {}
    
    if not marksheets:
        print("⚠️ No marksheets found in database for user:", username)
        return {}
    
    print(f"📚 Found {len(marksheets)} marksheet(s) for user: {username}")
    
    # Process all marksheets
    for marksheet in marksheets:
        subjects = marksheet.get("subjects", [])
        for subject_data in subjects:
            subject_name = subject_data.get("subject", "")
            grade = subject_data.get("grade", "")
            
            if subject_name and grade:
                # Map subject name to subject code
                subject_code = map_subject_name_to_code(subject_name, subjects_df)
                
                if subject_code:
                    # If multiple marksheets have same subject, keep the latest (overwrite)
                    grades_dict[subject_code] = grade
                    print(f"  ✓ Mapped: {subject_name} → {subject_code} (Grade: {grade})")
                else:
                    print(f"  ⚠ Could not map subject: {subject_name}")
    
    print(f"✅ Total mapped subjects: {len(grades_dict)}")
    return grades_dict

def get_user_grades(username: str = None, subjects_df: pd.DataFrame = None, grades_txt_path: str = None) -> dict:
    """
    Get user grades from various sources.
    Priority: MongoDB (PDF extraction) > text file
    
    Args:
        username: Username to fetch grades from MongoDB
        subjects_df: DataFrame with subjects to map names to codes
        grades_txt_path: Path to grades text file (fallback)
    
    Returns:
        dict: {subject_code: grade} format
    """
    # Try MongoDB first if username and subjects_df provided
    if username and subjects_df is not None:
        grades_dict = convert_pdf_grades_to_dict(username, subjects_df)
        if grades_dict:
            return grades_dict
    
    # Fallback to text file
    if grades_txt_path:
        return load_grades_from_txt(grades_txt_path)
    
    return {}

# --------------------------
# 2. Skill Profiling
# --------------------------
def build_skill_profile(grades_dict=None, subjects_df=None, username=None, grades_txt_path=None):
    """
    Build skill profile from grades.
    Can work with grades_dict directly or fetch from database.
    
    This function is backward compatible with orchestrator calls:
    - build_skill_profile(grades_dict, subjects_df) - works as before
    - build_skill_profile(grades_dict=None, subjects_df=df, username="user") - fetches from DB
    
    Args:
        grades_dict: Dictionary of {subject_code: grade} (optional)
        subjects_df: DataFrame with subjects information (required)
        username: Username to fetch grades from MongoDB (optional)
        grades_txt_path: Path to grades text file (optional, fallback)
    
    Returns:
        dict: Skill profile with skill names and scores
    """
    # Validate subjects_df
    if subjects_df is None:
        raise ValueError("subjects_df is required to build skill profile")
    
    # If grades_dict not provided or empty, try to get from database or file
    if not grades_dict or len(grades_dict) == 0:
        if username:
            # Try to fetch from database
            grades_dict = get_user_grades(
                username=username,
                subjects_df=subjects_df,
                grades_txt_path=grades_txt_path
            )
        elif grades_txt_path:
            # Fallback to text file
            grades_dict = get_user_grades(
                username=None,
                subjects_df=subjects_df,
                grades_txt_path=grades_txt_path
            )
        
        if not grades_dict or len(grades_dict) == 0:
            # Return empty profile if no grades found
            return {}
    
    return ai_utils.build_student_skill_profile(
        grades_dict, subjects_df, ai_utils.map_subject_to_skills
    )

# --------------------------
# 3. Charting
# --------------------------
def plot_skill_profile(skill_profile):
    if not skill_profile:
        print("⚠️ No skills found in profile.")
        return

    # Normalize for 0-100
    max_val, min_val = max(skill_profile.values()), min(skill_profile.values())
    viz = {
        k: ((v - min_val) / (max_val - min_val)) * 100 if max_val > min_val else 50
        for k, v in skill_profile.items()
    }

    top_skills = sorted(viz.items(), key=lambda x: x[1], reverse=True)[:15]
    radar_df = pd.DataFrame(top_skills, columns=["Skill", "Value"])
    bar_df = pd.DataFrame(top_skills, columns=["Skill", "Strength (%)"])

    # Radar Chart
    fig_radar = px.line_polar(
        radar_df, r="Value", theta="Skill", line_close=True,
        title="🎯 Skill Radar Chart (Top 15)"
    )
    fig_radar.update_traces(fill="toself", line_color="blue", fillcolor="rgba(0,100,200,0.3)")
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
    fig_radar.show()

    # Bar Chart
    fig_bar = px.bar(
        bar_df.sort_values("Strength (%)"),
        x="Strength (%)", y="Skill", orientation="h",
        color="Strength (%)", color_continuous_scale="viridis",
        title="📊 Skill Strength Bar Chart (Top 15)"
    )
    fig_bar.show()

def plot_subject_fit(grades_dict, subjects_df, skill_profile):
    # Compute strength scores using local_prediction model
    local_model = ai_utils.LocalPredictionModel()
    scores = {}
    for _, r in subjects_df.iterrows():
        subj_name = r.get("Subject Name", "")
        desc = r.get("Description", "")
        score = local_model.calculate_strength_score(grades_dict, subj_name, desc, subjects_df)
        scores[subj_name] = score

    '''df = pd.DataFrame(list(scores.items()), columns=["Subject", "Strength Score"])
    fig = px.bar(df, x="Subject", y="Strength Score", title="Subject Strength Scores")
    fig.show()'''

# --------------------------
# 4. Main Agent Runner
# --------------------------
def run_skill_profiler(subjects_xlsx_path: str, username: str = None, grades_txt_path: str = None, 
                       grades_dict: dict = None, show_plots: bool = True):
    """
    Main function to run skill profiler agent.
    Fetches grades from MongoDB (PDF extraction) or text file.
    
    Args:
        subjects_xlsx_path: Path to subjects Excel file (required)
        username: Username to fetch grades from MongoDB (optional, preferred)
        grades_txt_path: Path to grades text file (optional, fallback if no MongoDB data)
        grades_dict: Dictionary of grades (optional, will fetch from DB if not provided)
        show_plots: Whether to display plots (default: True)
    
    Returns:
        dict: Skill profile with skill names and scores
    """
    # Load subjects DataFrame
    subjects_df = pd.read_excel(subjects_xlsx_path)
    subjects_df.columns = [c.strip() for c in subjects_df.columns]
    
    # Get user grades from MongoDB or text file
    print("\n" + "="*60)
    print("📊 Building Skill Profile...")
    print("="*60)
    
    if grades_dict is None:
        grades_dict = get_user_grades(
            username=username,
            subjects_df=subjects_df,
            grades_txt_path=grades_txt_path
        )
        
        if not grades_dict:
            raise ValueError(
                "No grades found. Please:\n"
                "  1. Upload marksheets in the profile section, OR\n"
                "  2. Provide grades_dict or grades_txt_path parameter"
            )
    
    print(f"\n✅ Loaded {len(grades_dict)} subject grades")
    
    # Build skill profile
    skill_profile = build_skill_profile(grades_dict=grades_dict, subjects_df=subjects_df)
    
    # Display skill profile summary
    print("\n" + "="*60)
    print("🎯 Skill Profile Summary")
    print("="*60)
    
    if not skill_profile:
        print("⚠️ No skills found in profile.")
        return skill_profile
    
    # Sort skills by score
    sorted_skills = sorted(skill_profile.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n📈 Top Skills:")
    print("-" * 60)
    for i, (skill, score) in enumerate(sorted_skills[:10], 1):
        print(f"  {i:2d}. {skill:30s} : {score:6.2f}")
    
    print(f"\n📊 Total skills analyzed: {len(skill_profile)}")
    
    # Charts (optional)
    if show_plots:
        print("\n📊 Generating visualizations...")
        plot_skill_profile(skill_profile)
        plot_subject_fit(grades_dict, subjects_df, skill_profile)
    
    print("\n" + "="*60)
    return skill_profile


if __name__ == "__main__":
    # Example usage:
    # Option 1: Using MongoDB (username from session)
    # run_skill_profiler(
    #     subjects_xlsx_path="data/subjects.xlsx",
    #     username="testuser"  # Replace with actual username
    # )
    
    # Option 2: Using text file (fallback)
    run_skill_profiler(
        subjects_xlsx_path="data/subjects.xlsx",
        grades_txt_path="gradesheet.txt"  # Optional fallback
    )
