# agents/recommendation_agent.py

import pandas as pd
from collections import defaultdict
from utils import ai_utils
from utils.skills import SKILL_LABELS
def load_grades_from_txt(file_path: str) -> dict:
    grades = {}
    with open(file_path, "r") as f:
        for line in f:
            if ":" in line:
                subj, grade = line.strip().split(":")
                grades[subj.strip()] = grade.strip()
    return grades

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
def run_recommendation_agent(grades_txt_path, subjects_xlsx_path, next_sem):
    grades_dict = load_grades_from_txt(grades_txt_path)
    subjects_df = pd.read_excel(subjects_xlsx_path)
    
    rec_df, api_failures = generate_recommendations(grades_dict, subjects_df, next_sem)
    
    print("\n🏆 Recommended Electives for Next Semester\n")
    for basket, grp in rec_df.groupby("Basket"):
        print(f"Basket {basket}:")
        for idx, row in grp.iterrows():
            print(f"  {row['Subject']} | Strength: {row['Strength']} | Market: {row['MarketDemand']} | Combined: {row['CombinedScore']}")
        print("-"*50)
    
    if api_failures > 0:
        print(f"⚠️ {api_failures} subject(s) used fallback market scores due to API issues.")

if __name__ == "__main__":
    run_recommendation_agent(
        grades_txt_path="gradesheet.txt",
        subjects_xlsx_path="data/subjects.xlsx",
        next_sem=6
    )
