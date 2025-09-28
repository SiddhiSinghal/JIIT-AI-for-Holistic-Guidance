# app.py
import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from utils.ai_utils import (
    map_subject_to_skills, get_subject_market_score,
    build_student_skill_profile,
    score_subject_for_student,
    GRADE_MAP,
    compute_subject_score,
    compute_combined_recommendation_score,
    compute_local_strength_score,
)
from utils.skills import SKILL_LABELS

st.set_page_config(layout="wide", page_title="🎓 Smart Elective & MOOC Advisor")
st.title("🎓 Smart Elective & MOOC Advisor — Skill-label driven")

st.sidebar.header("Dataset & Settings")
FILE_PATH = "data/subjects.xlsx"

if not os.path.exists(FILE_PATH):
    st.sidebar.error(f"❌ Master dataset not found at `{FILE_PATH}`. Please place your file there.")
    st.stop()

master_df = pd.read_excel(FILE_PATH) if FILE_PATH.endswith(".xlsx") else pd.read_csv(FILE_PATH)
master_df.columns = [c.strip() for c in master_df.columns]

required = {"Semester", "Subject Code", "Subject Name", "Code", "Type"}
if not required.issubset(set(master_df.columns)):
    st.error(f"❌ Master file must contain columns: {required}")
    st.stop()


current_sem = st.sidebar.number_input("📌 Your current semester", min_value=5, max_value=8, value=5)
completed_semesters = list(range(1, current_sem))

st.header("1️⃣ Enter grades for subjects you've completed")
completed_df = master_df[master_df["Semester"].isin(completed_semesters)].copy()

if completed_df.empty:
    st.error("⚠️ No completed subjects found for the selected semester in dataset.")
    st.stop()

student_grades = {}

if "show_grade_form" not in st.session_state:
    st.session_state["show_grade_form"] = False
if "grades_entered" not in st.session_state:
    st.session_state["grades_entered"] = False
if "student_grades" not in st.session_state:
    st.session_state["student_grades"] = {}
if "student_profile" not in st.session_state:
    st.session_state["student_profile"] = {}

if st.button("✍️ Start Entering Grades"):
    st.session_state["show_grade_form"] = True

if st.session_state["show_grade_form"] and not st.session_state["grades_entered"]:
    st.info("Please fill in your grades below and click 'Submit Grades' when done.")

    for sem in sorted(completed_df["Semester"].unique()):
        st.subheader(f"Semester {sem}")
        sem_df = completed_df[completed_df["Semester"] == sem]

        for basket_code, basket_group in sem_df.groupby("Code"):
            if len(basket_group) == 1 or all(basket_group["Type"].isin(["C", "Core-Audit"])):
                for _, row in basket_group.iterrows():
                    code, name = row["Subject Code"], row["Subject Name"]
                    st.selectbox(
                        f"{name} ({code})",
                        options=list(GRADE_MAP.keys()),
                        index=list(GRADE_MAP.keys()).index("A"),
                        key=f"grade_{code}"
                    )

            else:
                st.markdown(f"**Basket {basket_code}** — Choose the elective you actually took:")
                elective_names = {
                    f"{r['Subject Name']} ({r['Subject Code']})": r["Subject Code"]
                    for _, r in basket_group.iterrows()
                }
                chosen_display = st.selectbox(
                    f"Select elective for Basket {basket_code}",
                    options=["-- Select --"] + list(elective_names.keys()),
                    key=f"elective_select_{basket_code}"
                )
                if chosen_display and chosen_display != "-- Select --":
                    chosen_code = elective_names[chosen_display]
                    st.selectbox(
                        f"Grade for {chosen_display}",
                        options=list(GRADE_MAP.keys()),
                        index=list(GRADE_MAP.keys()).index("A"),
                        key=f"grade_{chosen_code}"
                    )

    if st.button("✅ Submit Grades"):
        built_grades = {}
        for sem in sorted(completed_df["Semester"].unique()):
            sem_df = completed_df[completed_df["Semester"] == sem]
            for basket_code, basket_group in sem_df.groupby("Code"):
                if len(basket_group) == 1 or all(basket_group["Type"].isin(["C", "Core-Audit"])):
                    for _, row in basket_group.iterrows():
                        code = row["Subject Code"]
                        grade_val = st.session_state.get(f"grade_{code}", None)
                        if grade_val:
                            built_grades[code] = grade_val

                else:
                    chosen_display = st.session_state.get(f"elective_select_{basket_code}", "-- Select --")
                    if chosen_display and chosen_display != "-- Select --":
                        elective_map = {f"{r['Subject Name']} ({r['Subject Code']})": r["Subject Code"] for _, r in basket_group.iterrows()}
                        chosen_code = elective_map.get(chosen_display)
                        if chosen_code:
                            grade_val = st.session_state.get(f"grade_{chosen_code}", None)
                            if grade_val:
                                built_grades[chosen_code] = grade_val

        st.session_state["student_grades"] = built_grades
        st.session_state["grades_entered"] = True

        with st.spinner("Computing your skill profile..."):
            profile = build_student_skill_profile(st.session_state["student_grades"], completed_df, map_subject_to_skills)
            st.session_state["student_profile"] = profile or {}

        st.success("✅ Grades submitted and skill profile computed. You can now view recommendations below.")

st.markdown("---")
if not st.session_state.get("grades_entered", False):
    st.header("2️⃣ Build your skill profile")
    st.info("Please click 'Start Entering Grades' and submit your grades to reveal skill profile and recommendations.")
else:
    st.header("2️⃣ Build your skill profile")

    if st.button("⚡ Build Skill Profile"):
        if not st.session_state.get("student_grades", {}):
            st.warning("⚠️ Please enter grades first before building skill profile.")
        else:
            with st.spinner("Building skill profile..."):
                profile = build_student_skill_profile(st.session_state.get("student_grades", {}), completed_df, map_subject_to_skills)

                if not profile:
                    st.warning("⚠️ No skills derived. Check your inputs.")
                else:
                    max_val, min_val = max(profile.values()), min(profile.values())
                    viz = {k: ((v - min_val) / (max_val - min_val)) * 100 if max_val > min_val else 50
                           for k, v in profile.items()}

                    top_skills = sorted(viz.items(), key=lambda x: x[1], reverse=True)[:15]
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("🎯 Skill Radar Chart (Top 15)")
                        radar_df = pd.DataFrame(top_skills, columns=["Skill", "Value"])
                        fig = px.line_polar(radar_df, r="Value", theta="Skill", line_close=True)
                        fig.update_traces(fill="toself", line_color="blue", fillcolor="rgba(0,100,200,0.3)")
                        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500)
                        st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        st.subheader("📊 Skill Strength Bar Chart")
                        bar_df = pd.DataFrame(top_skills, columns=["Skill", "Strength (%)"])
                        fig_bar = px.bar(bar_df.sort_values("Strength (%)"),
                                         x="Strength (%)", y="Skill", orientation='h',
                                         color="Strength (%)", color_continuous_scale="viridis")
                        st.plotly_chart(fig_bar, use_container_width=True)

                    st.session_state["student_profile"] = profile

st.markdown("---")
st.header("3️⃣ Recommendations for Next Semester")

next_sem = current_sem + 1
next_df = master_df[(master_df["Semester"] == next_sem) & (master_df["Type"].isin(["E", "OC"]))]

if next_df.empty:
    st.info("No electives/optional cores for next semester.")
    st.stop()

st.info(f"📚 {len(next_df['Code'].unique())} baskets | {len(next_df)} subjects found for Sem {next_sem}")

if not st.session_state.get("grades_entered", False):
    st.warning("Please enter and submit your grades first to compute personalized recommendations.")
    st.stop()

if st.button("🔍 Map next-semester subjects to skills"):
    with st.spinner("Mapping subjects..."):
        for _, r in next_df.iterrows():
            _ = map_subject_to_skills(r["Subject Name"], r.get("Description", ""))
    st.success("✅ Mapping cached.")

view = st.radio("Choose view:", ["Strength Analysis", "Market Trend Analysis", "Combined Recommendation"])

student_profile = st.session_state.get("student_profile", {})
student_grades = st.session_state.get("student_grades", {})
subject_rows, api_failures = [], 0

for _, r in next_df.iterrows():
    subj_code, subj_name, desc = r["Subject Code"], r["Subject Name"], r.get("Description", "")
    subj_skill_map = map_subject_to_skills(subj_name, desc)

    strength_score = compute_local_strength_score(student_grades, subj_name, desc, master_df, map_subject_to_skills)
    try:
        market_score_100 = get_subject_market_score(subj_name, desc)
        market_score = (market_score_100 / 100.0) * 10.0
    except Exception:
        api_failures += 1
        market_score_100, market_score = 60.0, 6.0

    subject_rows.append({
        "Basket": r["Code"],
        "Subject Code": subj_code,
        "Subject Name": subj_name,
        "Skills (sample)": ", ".join(list(subj_skill_map.keys())[:4]),
        "Strength Score": round(float(strength_score) if not np.isnan(strength_score) else 0.0, 2),
        "Market Score (0-10)": round(market_score, 2),
        "Market Score (0-100)": round(market_score_100, 2)
    })

results_df = pd.DataFrame(subject_rows)

if view == "Strength Analysis":
    st.subheader("💪 Ranked by Strength")
    for basket, grp in results_df.groupby("Basket"):
        sorted_grp = grp.sort_values("Strength Score", ascending=False).reset_index(drop=True)
        sorted_grp["Rank"] = range(1, len(sorted_grp)+1)
        st.dataframe(sorted_grp.drop(columns=["Skills (sample)"],), use_container_width=True)
        st.success(f"🏆 Best for Basket {basket}: {sorted_grp.iloc[0]['Subject Name']} ({sorted_grp.iloc[0]['Strength Score']:.2f})")
        st.markdown("---")

elif view == "Market Trend Analysis":
    st.subheader("📈 Ranked by Market Demand")
    for basket, grp in results_df.groupby("Basket"):
        sorted_grp = grp.sort_values("Market Score (0-100)", ascending=False).reset_index(drop=True)
        sorted_grp["Rank"] = range(1, len(sorted_grp)+1)
        st.dataframe(sorted_grp.drop(columns=["Skills (sample)"],), use_container_width=True)
        st.success(f"🏆 Market hotpick for Basket {basket}: {sorted_grp.iloc[0]['Subject Name']} ({sorted_grp.iloc[0]['Market Score (0-100)']:.1f})")
        st.markdown("---")

else:
    st.subheader("⚖️ Combined Recommendation")
    w_strength = st.slider("Weight for Strength (%)", 0, 100, 60)
    w_market = 100 - w_strength

    results_df["Combined"] = results_df.apply(
        lambda row: compute_combined_recommendation_score(
            row["Strength Score"],
            row["Market Score (0-10)"],
            w_strength/100,
            w_market/100
        ), axis=1
    )

    for basket, grp in results_df.groupby("Basket"):
        sorted_grp = grp.sort_values("Combined", ascending=False).reset_index(drop=True)
        sorted_grp["Rank"] = range(1, len(sorted_grp)+1)
        st.dataframe(sorted_grp.drop(columns=["Skills (sample)"],), use_container_width=True)
        st.success(f"🏆 Best overall for Basket {basket}: {sorted_grp.iloc[0]['Subject Name']} ({sorted_grp.iloc[0]['Combined']:.2f})")
        st.markdown("---")

st.success("✅ 100% AI-Free — Uses only local analysis + free job APIs")
if api_failures > 0:
    st.warning(f"⚠️ {api_failures} subject(s) used fallback scores due to API issues.")
