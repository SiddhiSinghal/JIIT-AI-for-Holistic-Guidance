# agents/skill_profiler_agent.py

import pandas as pd
import plotly.express as px
from collections import defaultdict

from utils import ai_utils
from utils.skills import SKILL_LABELS

# --------------------------
# 1. Parse Grades from .txt
# --------------------------
def load_grades_from_txt(file_path: str) -> dict:
    grades = {}
    with open(file_path, "r") as f:
        for line in f:
            if ":" in line:
                subj, grade = line.strip().split(":")
                grades[subj.strip()] = grade.strip()
    return grades

# --------------------------
# 2. Skill Profiling
# --------------------------
def build_skill_profile(grades_dict, subjects_df):
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
def run_skill_profiler(grades_txt_path, subjects_xlsx_path):
    # Load inputs
    grades_dict = load_grades_from_txt(grades_txt_path)
    subjects_df = pd.read_excel(subjects_xlsx_path)

    # Build skill profile
    skill_profile = build_skill_profile(grades_dict, subjects_df)

    # Charts
    plot_skill_profile(skill_profile)
    plot_subject_fit(grades_dict, subjects_df, skill_profile)


if __name__ == "__main__":
    # Example run
    run_skill_profiler(
        grades_txt_path="gradesheet.txt",
        subjects_xlsx_path="data/subjects.xlsx"
    )
