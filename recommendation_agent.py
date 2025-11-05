# recommendation_agent.py

import pandas as pd
from utils import ai_utils
from utils.skills import SKILL_LABELS
from pymongo import MongoClient
from difflib import SequenceMatcher

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
# 2. Build Skill Profile
# --------------------------
def build_skill_profile(grades_dict, subjects_df):
    return ai_utils.build_student_skill_profile(
        grades_dict, subjects_df, ai_utils.map_subject_to_skills
    )


# --------------------------
# 3. Recommendation Engine
# --------------------------
def generate_recommendations(grades_dict, subjects_df, next_sem):
    local_model = ai_utils.LocalPredictionModel()
    skill_profile = build_skill_profile(grades_dict, subjects_df)
    
    # Filter subjects for next semester (Electives/Optional Core)
    next_df = subjects_df[
        (subjects_df["Semester"] == next_sem) &
        (subjects_df["Type"].isin(["E", "OC"]))
    ]
    
    results = []
    api_failures = 0

    # Temporarily silence internal print statements from ai_utils
    import io, sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()  # Redirect prints to a dummy stream

    for _, r in next_df.iterrows():
        subj_name = r["Subject Name"]
        desc = r.get("Description", "")
        basket = r["Code"]
        
        # Strength score
        strength_score = local_model.calculate_strength_score(
            grades_dict, subj_name, desc, subjects_df
        )

        # Market score (safely handled)
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

    sys.stdout = old_stdout  # Restore normal printing

    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    return results_df.sort_values(["Basket", "CombinedScore"], ascending=[True, False]), api_failures


# --------------------------
# 4. Main Runner
# --------------------------
def run_recommendation_agent(subjects_xlsx_path: str, next_sem: int, username: str = None, grades_txt_path: str = None):
    """
    Main function to run recommendation agent.
    Fetches grades from MongoDB (PDF extraction) or text file.
    
    Args:
        subjects_xlsx_path: Path to subjects Excel file (required)
        next_sem: Next semester number (required)
        username: Username to fetch grades from MongoDB (optional, preferred)
        grades_txt_path: Path to grades text file (optional, fallback if no MongoDB data)
    
    Returns:
        Tuple of (results_df, api_failures)
    """
    # Load subjects DataFrame
    subjects_df = pd.read_excel(subjects_xlsx_path)
    subjects_df.columns = [c.strip() for c in subjects_df.columns]
    
    # Get user grades from MongoDB or text file
    print("\n" + "="*60)
    print("📊 Fetching User Grades...")
    print("="*60)
    
    grades_dict = get_user_grades(
        username=username,
        subjects_df=subjects_df,
        grades_txt_path=grades_txt_path
    )
    
    if not grades_dict:
        raise ValueError(
            "No grades found. Please:\n"
            "  1. Upload marksheets in the profile section, OR\n"
            "  2. Provide grades_txt_path parameter"
        )
    
    print(f"\n✅ Loaded {len(grades_dict)} subject grades")
    print("\n" + "="*60)
    print("🎯 Generating Recommendations...")
    print("="*60)
    
    # Generate recommendations
    rec_df, api_failures = generate_recommendations(grades_dict, subjects_df, next_sem)
    
    # Display results
    print("\n" + "="*60)
    print(f"🏆 Recommended Electives for Semester {next_sem}")
    print("="*60)
    
    if rec_df.empty:
        print("⚠️ No electives found for the next semester.")
        return rec_df, api_failures
    
    for basket, grp in rec_df.groupby("Basket"):
        print(f"\n📦 Basket {basket}:")
        print("-" * 60)
        for idx, row in grp.iterrows():
            print(f"  • {row['Subject']}")
            print(f"    Strength Score: {row['Strength']:.2f} | "
                  f"Market Demand: {row['MarketDemand']:.2f} | "
                  f"Combined Score: {row['CombinedScore']:.2f}")
    
    if api_failures > 0:
        print(f"\n⚠️ {api_failures} subject(s) used fallback market scores due to API issues.")
    
    print("\n" + "="*60)
    return rec_df, api_failures


if __name__ == "__main__":
    # Example usage:
    # Option 1: Using MongoDB (username from session)
    # run_recommendation_agent(
    #     subjects_xlsx_path="data/subjects.xlsx",
    #     next_sem=6,
    #     username="testuser"  # Replace with actual username
    # )
    
    # Option 2: Using text file (fallback)
    run_recommendation_agent(
        subjects_xlsx_path="data/subjects.xlsx",
        next_sem=6,
        grades_txt_path="gradesheet.txt"  # Optional fallback
    )
