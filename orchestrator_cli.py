import importlib
import sys
import os
import json
from markupsafe import Markup
from dotenv import load_dotenv
import re
from markupsafe import Markup

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


# --------------------------------------------------
# CLASSIFY PROMPT
# --------------------------------------------------
def classify_prompt(prompt: str) -> str:
    """Classify prompt type based on keywords."""
    prompt = prompt.lower()

    if any(k in prompt for k in ["career", "job role", "profession", "scope", "salary"]):
        return "career"
    elif any(k in prompt for k in ["roadmap", "steps", "plan", "path"]):
        return "roadmap"
    elif any(k in prompt for k in ["linkedin", "post", "content", "write"]):
        return "linkedin"
    elif any(k in prompt for k in ["fact", "true or false", "verify", "check"]):
        return "factcheck"
    elif any(k in prompt for k in ["research", "find", "study", "analyze"]):
        return "research"
    elif any(k in prompt for k in ["subject", "elective", "semester", "recommend course", "suggest course"]):
        return "subject"
    elif any(k in prompt for k in ["recommend", "placement", "top job", "suggest jobs"]):
        return "job"
    elif any(k in prompt for k in ["skill", "strength", "weakness", "profile"]):
        return "skills"
    elif any(k in prompt for k in ["market", "demand", "trend", "score"]):
        return "market"
    elif any(k in prompt for k in ["mooc", "nptel", "course mapping", "pdf", "subject code"]):
        return "mooc"
    else:
        return "unknown"


# --------------------------------------------------
# RUN LLM AGENTS
# --------------------------------------------------
def run_llm_agent(agent_key: str, prompt: str):
    """Run LLM-based agent depending on key."""
    mod = importlib.import_module(LLM_AGENTS.get(agent_key))
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
    return f"⚠️ No valid LLM agent found for '{agent_key}'."


# --------------------------------------------------
# RUN NON-LLM AGENTS

def run_non_llm_agent(agent_key: str, username=None, last_user_message=None):
    """Run non-LLM ML-based agents (job, subject, skills, etc.)."""
    if agent_key == "job":
        from agents.job_recommendation import recommend_jobs
        return recommend_jobs()

    elif agent_key == "skills":
        from agents.skill_profiler_agent import run_skill_profiler
        print("🎯 Running Skill Profiler...")
        profile = run_skill_profiler("data/subjects.xlsx", username)
        return "✅ Skill profiler completed successfully."

    elif agent_key == "market":
        from agents.market_score_agent import MarketScoreAgent
        agent = MarketScoreAgent()
        result = agent.get_score("Artificial Intelligence")
        return json.dumps(result, indent=2)

    elif agent_key == "subject":
        from agents.recommendation_agent import run_recommendation_agent

        # 🧠 Safely detect semester number
        next_sem = 6  # Default fallback
        if isinstance(last_user_message, str):  # ✅ Make sure it's a string
            match = re.search(r"(?:sem|semester)\s*(\d+)", last_user_message.lower())
            if match:
                next_sem = int(match.group(1))

        print(f"📘 Detected next semester: {next_sem}")
        html_output = run_recommendation_agent(username, "data/subjects.xlsx", next_sem)
        return Markup(html_output)

    else:
        return f"⚠️ No valid ML agent found for '{agent_key}'."



# --------------------------------------------------
# MAIN ORCHESTRATOR
# --------------------------------------------------
def orchestrate(prompt: str, username=None, last_user_message=None):

    """Main orchestrator logic for CLI or Flask route."""
    print("\n🧠 Classifying task type...")
    task_type = classify_prompt(prompt)

    if task_type == "unknown":
        return "⚠️ Sorry, I couldn’t determine what you’re asking about."

    if task_type in LLM_AGENTS:
        print(f"🧩 Using LLM-based agent: {task_type}")
        result = run_llm_agent(task_type, prompt)
    elif task_type in NON_LLM_AGENTS:
        result = run_non_llm_agent(task_type, username, last_user_message)

    else:
        result = "❌ No suitable agent found."

    return result


# --------------------------------------------------
# TEST RUN (CLI MODE)
# --------------------------------------------------
if __name__ == "__main__":
    print("=== 🤖 Multi-Agent Orchestrator ===")
    user_prompt = input("Enter your query: ").strip()
    response = orchestrate(user_prompt, username="ss")
    print("\nResponse:\n", response)
