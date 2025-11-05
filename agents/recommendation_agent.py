# agents/recommendation_agent.py

import pandas as pd
from collections import defaultdict
from utils import ai_utils
from utils.skills import SKILL_LABELS
from models import UserScores, User
from flask_login import current_user
from pymongo import MongoClient
from difflib import SequenceMatcher

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

def fetch_grades_from_database(user_id=None, username=None, subjects_df=None):
    """
    Fetch user grades from database.
    Similar to job_recommendation.py, this fetches user data from database.
    For grades, it tries to fetch from MongoDB if available, otherwise returns empty dict.
    """
    # Try to get user_id from current_user if available
    if user_id is None:
        try:
            if hasattr(current_user, 'id') and current_user.is_authenticated:
                user_id = current_user.id
                if not username and hasattr(current_user, 'name'):
                    username = current_user.name
        except Exception:
            pass
    
    # Try to fetch from MongoDB using username (preferred method)
    if username and subjects_df is not None:
        grades_dict = convert_pdf_grades_to_dict(username, subjects_df)
        if grades_dict:
            return grades_dict
    
    # Fallback: Try to fetch from MongoDB using user_id (SQLAlchemy User model)
    if user_id is None:
        return {}
    
    try:
        from pymongo import MongoClient
        
        # Get user directly from User model
        user = User.query.filter_by(id=user_id).first()
        if user and hasattr(user, 'email'):
            client = MongoClient("mongodb://localhost:27017/")
            db = client["holistic_guidance"]
            users_collection = db["users"]
            
            # Try to find user in MongoDB by email or username
            mongo_user = users_collection.find_one({"email": user.email})
            if not mongo_user:
                # Try by username if email doesn't match
                mongo_user = users_collection.find_one({"username": user.name})
            
            if mongo_user and subjects_df is not None:
                # Map subject names to codes
                username_for_mapping = mongo_user.get("username", user.name)
                return convert_pdf_grades_to_dict(username_for_mapping, subjects_df)
    except Exception as e:
        # MongoDB not available or error, continue with empty dict
        pass
    
    # Return empty dict if no grades found
    return {}

def get_user_grades(grades_dict=None, grades_txt_path=None, user_id=None, username=None, subjects_df=None):
    """
    Get user grades from various sources.
    Priority: grades_dict > database (MongoDB with mapping) > text file
    
    Args:
        grades_dict: Pre-provided grades dict (optional)
        grades_txt_path: Path to grades text file (optional, fallback)
        user_id: User ID from SQLAlchemy (optional)
        username: Username from MongoDB (optional, preferred)
        subjects_df: DataFrame with subjects for mapping (required for database fetching)
    
    Returns:
        dict: {subject_code: grade} format
    """
    if grades_dict is not None:
        return grades_dict
    
    # Try to fetch from database with mapping
    if (user_id or username) and subjects_df is not None:
        db_grades = fetch_grades_from_database(user_id=user_id, username=username, subjects_df=subjects_df)
        if db_grades:
            return db_grades
    
    # Fallback to text file if provided
    if grades_txt_path:
        return load_grades_from_txt(grades_txt_path)
    
    return {}

# --------------------------
# 2. Build Skill Profile
# --------------------------
def build_skill_profile(grades_dict, subjects_df):
    return ai_utils.build_student_skill_profile(
        grades_dict, subjects_df, ai_utils.map_subject_to_skills
    )

# --------------------------
# 3. Recommendation Engine
# --------------------------
def generate_recommendations(grades_dict=None, subjects_df=None, next_sem=None, grades_txt_path=None, user_id=None, username=None):
    """
    Generate recommendations for next semester electives.
    
    Args:
        grades_dict: Dictionary of subject codes to grades (optional, will fetch from DB if not provided)
        subjects_df: DataFrame containing subject information (required)
        next_sem: Next semester number (required)
        grades_txt_path: Path to grades text file (optional, fallback)
        user_id: User ID to fetch grades from database (optional, uses current_user if not provided)
        username: Username to fetch from MongoDB (optional, preferred over user_id)
    
    Returns:
        Tuple of (results_df, api_failures)
    """
    # Get grades from database or provided source
    if grades_dict is None:
        if subjects_df is None:
            raise ValueError("subjects_df is required to fetch grades from database")
        grades_dict = get_user_grades(
            grades_dict=None, 
            grades_txt_path=grades_txt_path, 
            user_id=user_id,
            username=username,
            subjects_df=subjects_df
        )
    
    if not grades_dict:
        raise ValueError("No grades found. Please provide grades_dict, grades_txt_path, or ensure user has grades in database.")
    
    if subjects_df is None:
        raise ValueError("subjects_df is required")
    
    if next_sem is None:
        raise ValueError("next_sem is required")
    
    local_model = ai_utils.LocalPredictionModel()
    skill_profile = build_skill_profile(grades_dict, subjects_df)
    
    # Filter subjects for next semester (Electives/Optional Core)
    next_df = subjects_df[
        (subjects_df["Semester"] == next_sem) &
        (subjects_df["Type"].isin(["E", "OC"]))
    ]
    
    results = []
    api_failures = 0
    
    for _, r in next_df.iterrows():
        subj_name = r["Subject Name"]
        desc = r.get("Description", "")
        basket = r["Code"]
        
        # Strength score
        strength_score = local_model.calculate_strength_score(
            grades_dict, subj_name, desc, subjects_df
        )
        
        # Market score (simulate API fallback like web app)
        try:
            market_score_100 = ai_utils.get_subject_market_score(subj_name, desc)
            market_score = (market_score_100 / 100.0) * 10.0
        except Exception:
            api_failures += 1
            market_score_100, market_score = 60.0, 6.0
        
        # Combined score
        combined_score = ai_utils.compute_combined_recommendation_score(
            strength_score, market_score, 0.6, 0.4
        )
        
        results.append({
            "Basket": basket,
            "Subject": subj_name,
            "Strength": round(strength_score, 2),
            "MarketDemand": round(market_score_100, 2),
            "CombinedScore": round(combined_score, 2)
        })
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    return results_df.sort_values(["Basket", "CombinedScore"], ascending=[True, False]), api_failures

# --------------------------
# 4. Main Runner
# --------------------------
def run_recommendation_agent(subjects_xlsx_path, next_sem, grades_txt_path=None, grades_dict=None, user_id=None, username=None):
    """
    Main function to run recommendation agent.
    Similar to job_recommendation.py, this fetches data from database.
    
    Args:
        subjects_xlsx_path: Path to subjects Excel file (required)
        next_sem: Next semester number (required)
        grades_txt_path: Path to grades text file (optional, fallback if no DB grades)
        grades_dict: Dictionary of grades (optional, will fetch from DB if not provided)
        user_id: User ID to fetch from database (optional, uses current_user if not provided)
        username: Username to fetch from MongoDB (optional, preferred over user_id)
    
    Returns:
        Tuple of (results_df, api_failures)
    """
    # Load subjects DataFrame first (needed for mapping)
    subjects_df = pd.read_excel(subjects_xlsx_path)
    subjects_df.columns = [c.strip() for c in subjects_df.columns]
    
    # Get grades from database or provided source (with proper mapping)
    grades_dict = get_user_grades(
        grades_dict=grades_dict, 
        grades_txt_path=grades_txt_path, 
        user_id=user_id,
        username=username,
        subjects_df=subjects_df
    )
    
    if not grades_dict:
        raise ValueError("No grades found. Please provide grades_dict, grades_txt_path, or ensure user has grades in database.")
    
    rec_df, api_failures = generate_recommendations(
        grades_dict=grades_dict, 
        subjects_df=subjects_df, 
        next_sem=next_sem,
        username=username,
        user_id=user_id
    )
    
    print("\n🏆 Recommended Electives for Next Semester\n")
    for basket, grp in rec_df.groupby("Basket"):
        print(f"Basket {basket}:")
        for idx, row in grp.iterrows():
            print(f"  {row['Subject']} | Strength: {row['Strength']} | Market: {row['MarketDemand']} | Combined: {row['CombinedScore']}")
        print("-"*50)
    
    if api_failures > 0:
        print(f"⚠️ {api_failures} subject(s) used fallback market scores due to API issues.")

if __name__ == "__main__":
    # Example usage - can work with database or file
    # For database usage, ensure user is logged in via Flask-Login
    run_recommendation_agent(
        subjects_xlsx_path="data/subjects.xlsx",
        next_sem=6,
        grades_txt_path="gradesheet.txt"  # Optional fallback
    )
