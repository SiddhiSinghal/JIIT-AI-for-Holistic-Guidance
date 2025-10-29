# orchestrator_cli.py
import importlib
import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()

# === Categorize agents ===
LLM_AGENTS = {
    "career": "agents.career_exploration",
    "roadmap": "agents.roadmap",
    "linkedin": "agents.linkedin_post_generator",
    "research": "agents.web_researcher",
    "factcheck": "agents.fact_checker"
}

NON_LLM_AGENTS = {
    "job": "agents.job_recommendation",
    "skills": "agents.skill_profiler_agent",
    "market": "agents.market_score_agent"
}


def classify_prompt(prompt: str) -> str:
    """Roughly classify prompt type based on keywords."""
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
    elif any(k in prompt for k in ["recommend", "suggest jobs", "placement"]):
        return "job"
    elif any(k in prompt for k in ["skill", "profile", "strengths", "weakness"]):
        return "skills"
    elif any(k in prompt for k in ["market", "demand", "trend", "score"]):
        return "market"
    else:
        return "unknown"


def run_llm_agent(agent_key: str, prompt: str):
    """Run LLM-based agent depending on key."""
    if agent_key == "career":
        mod = importlib.import_module(LLM_AGENTS[agent_key])
        result = mod.get_career_info(prompt)
    elif agent_key == "roadmap":
        mod = importlib.import_module(LLM_AGENTS[agent_key])
        # Dummy user scores
        result = mod.get_roadmap(prompt, {"DSA": 8, "Math": 7}, weeks=10)
    elif agent_key == "linkedin":
        mod = importlib.import_module(LLM_AGENTS[agent_key])
        result = mod.generate_linkedin_post("AI", ["LLMs are transforming industry", "Focus on practical application"])
    elif agent_key == "research":
        mod = importlib.import_module(LLM_AGENTS[agent_key])
        result = mod.run_research(prompt)
    elif agent_key == "factcheck":
        mod = importlib.import_module(LLM_AGENTS[agent_key])
        result = mod.fact_check(prompt)
    else:
        result = f"No valid LLM agent found for '{agent_key}'"
    return result


def run_non_llm_agent(agent_key: str):
    """Run non-LLM ML-based agent."""
    if agent_key == "job":
        mod = importlib.import_module(NON_LLM_AGENTS[agent_key])
        result = mod.recommend_jobs()
    elif agent_key == "skills":
        mod = importlib.import_module(NON_LLM_AGENTS[agent_key])
        result = mod.profile_skills({"DSA": 8, "CN": 6, "Aptitude": 7})
    elif agent_key == "market":
        mod = importlib.import_module(NON_LLM_AGENTS[agent_key])
        result = mod.get_market_score("AI Engineer")
    else:
        result = f"No valid ML agent found for '{agent_key}'"
    return result


def orchestrate(prompt: str):
    """Main orchestrator logic for CLI"""
    print("\n🧠 Classifying task type...")
    task_type = classify_prompt(prompt)

    if task_type == "unknown":
        print("⚠️ Could not determine which agent to use.")
        return

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
    except:
        print(result)


if __name__ == "__main__":
    print("=== 🤖 Multi-Agent CLI Orchestrator ===")
    user_prompt = input("\nEnter your query: ").strip()
    orchestrate(user_prompt)
