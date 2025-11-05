# orchestrator_cli.py
import importlib
import sys
import os
import json
import subprocess
from dotenv import load_dotenv
from flask import session

load_dotenv()

# === Categorize agents ===
LLM_AGENTS = {
    "career": "agents.career_exploration",
    "roadmap": "agents.roadmap",
    "linkedin": "agents.linkedin_post_generator",
    "research": "agents.web_researcher",
    "factcheck": "agents.fact_checker",
    "mooc": "agents.mooc"
}

NON_LLM_AGENTS = {
    "job": "agents.job_recommendation",
    "skills": "agents.skill_profiler_agent",
    "market": "agents.market_score_agent",
    "subject": "agents.recommendation_agent"
}


# ==================== CLASSIFIER ====================
def classify_prompt(prompt: str) -> str:
    """Identify the user's intent (LLM vs ML agent)."""
    prompt = prompt.lower().strip()

    # 🔹 JOB RECOMMENDATION INTENT
    job_keywords = [
        "job", "jobs", "recommendation", "recommendations",
        "top job", "top jobs", "best job",
        "best career", "suggest job", "suggest me job",
        "career prediction", "which job", "job role",
        "my top job", "find job", "career path"
    ]
    if any(k in prompt for k in job_keywords):
        print("🎯 Detected JOB intent")
        return "job"

    # 🔹 Career exploration
    if any(k in prompt for k in ["career", "profession", "scope", "salary"]):
        return "career"

    # 🔹 Roadmap
    elif any(k in prompt for k in ["roadmap", "steps", "plan", "path"]):
        return "roadmap"

    # 🔹 LinkedIn Post
    elif any(k in prompt for k in ["linkedin", "post", "content", "write"]):
        return "linkedin"

    # 🔹 Fact-check
    elif any(k in prompt for k in ["fact", "true or false", "verify", "check"]):
        return "factcheck"

    # 🔹 Research
    elif any(k in prompt for k in ["research", "find", "study", "analyze"]):
        return "research"

    # 🔹 Subject recommendation
    elif any(k in prompt for k in ["subject", "semester", "recommend subjects"]):
        return "subject"

    # 🔹 Skills analysis
    elif any(k in prompt for k in ["skill", "profile", "strengths", "weakness"]):
        return "skills"

    # 🔹 Market demand
    elif any(k in prompt for k in ["market", "demand", "trend", "score"]):
        return "market"

    # 🔹 MOOC Mapping
    elif any(k in prompt for k in ["mooc", "nptel", "course mapping", "pdf", "subject code", "department", "credits"]):
        return "mooc"

    print("⚠️ Unknown task type detected")
    return "unknown"


# ==================== LLM AGENTS ====================
def run_llm_agent(agent_key: str, prompt: str):
    """Run LLM-based agents."""
    if agent_key not in LLM_AGENTS:
        return f"❌ Unknown LLM agent: {agent_key}"

    mod = importlib.import_module(LLM_AGENTS[agent_key])

    if agent_key == "career":
        return mod.get_career_info(prompt)
    elif agent_key == "roadmap":
        return mod.get_roadmap(prompt, {"DSA": 8, "Math": 7}, weeks=10)
    elif agent_key == "linkedin":
        return mod.generate_linkedin_post("AI", ["LLMs are transforming industry", "Focus on practical application"])
    elif agent_key == "research":
        return mod.run_research(prompt)
    elif agent_key == "factcheck":
        return mod.fact_check(prompt)
    elif agent_key == "mooc":
        pdf_path = os.path.join(os.path.dirname(mod.__file__), "uu.pdf")
        return mod.run_pdf_mooc_query(prompt, pdf_path)
    else:
        return f"No handler implemented for {agent_key}"


# ==================== NON-LLM AGENTS ====================
def run_non_llm_agent(agent_key: str, username: str = None):
    """Run non-LLM ML-based agent."""
    from flask import session

    if agent_key == "job":
        from agents.job_recommendation import recommend_jobs
        print("🚀 Fetching job recommendations based on your marks...")
        return recommend_jobs(username)

    elif agent_key == "skills":
        print("🚀 Running Skill Profiler Agent...")
        from agents.skill_profiler_agent import run_skill_profiler

        try:
            skill_profile = run_skill_profiler(
                subjects_xlsx_path="data/subjects.xlsx",
                username=username,
                show_plots=False  # Ensure we don’t pop up any graphs
            )

            if not skill_profile:
                return "⚠️ No skill data found. Please upload your marksheet first."

            # Sort top 10 skills
            top_skills = sorted(skill_profile.items(), key=lambda x: x[1], reverse=True)[:10]

            # --- Formatted Text ---
            formatted_text = f"<b>🎯 Top Skills for {username}</b><br><br>"
            for skill, score in top_skills:
                formatted_text += f"• {skill}: {score:.2f}<br>"

            # --- Progress Bars (HTML) ---
            bars_html = "<div style='margin-top:10px;'>"
            for skill, score in top_skills:
                color = (
                    "#4CAF50" if score >= 8 else
                    "#FFC107" if score >= 6 else
                    "#FF5722"
                )
                width = min(100, int(score * 10))
                bars_html += f"""
                <div style="margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;font-size:14px;">
                        <span>{skill}</span><span>{score:.2f}</span>
                    </div>
                    <div style="background:#e0e0e0;border-radius:8px;height:10px;width:80%;">
                        <div style="width:{width}%;background:{color};height:10px;border-radius:8px;"></div>
                    </div>
                </div>
                """
            bars_html += "</div>"

            return formatted_text + bars_html

        except Exception as e:
            return f"⚠️ Error analyzing skills: {str(e)}"

    elif agent_key == "market":
        from agents.market_score_agent import MarketScoreAgent
        agent = MarketScoreAgent()
        result = agent.get_score("Artificial Intelligence")
        return f"📊 Market Score for {result['subject']}: {result['market_score']} ({result['meaning']})"

    else:
        return f"❌ No valid ML agent found for '{agent_key}'"


# ==================== ORCHESTRATOR ====================
def orchestrate(prompt: str):
    """Main orchestrator logic for chat or CLI."""
    print("\n🧠 Classifying task type...")
    task_type = classify_prompt(prompt)

    if task_type == "unknown":
        print("⚠️ Could not determine which agent to use.")
        return "⚠️ Could not determine task type."

    if task_type in LLM_AGENTS:
        print(f"🧩 Using LLM-based agent: {task_type}")
        result = run_llm_agent(task_type, prompt)
    elif task_type in NON_LLM_AGENTS:
        print(f"🧩 Using ML-based agent: {task_type}")
        result = run_non_llm_agent(task_type)
    else:
        result = "❌ No suitable agent found."

    print("\n✅ Result:")
    try:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception:
        print(result)

    return result


# ==================== CLI MODE ====================
if __name__ == "__main__":
    print("=== 🤖 Multi-Agent CLI Orchestrator ===")
    user_prompt = input("\nEnter your query: ").strip()
    orchestrate(user_prompt)
