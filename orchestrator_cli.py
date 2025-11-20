import importlib
import sys
import os
import json
from markupsafe import Markup
from dotenv import load_dotenv
import re
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



# ==================== CLASSIFIER ====================
def classify_prompt(prompt: str) -> str:
    """Identify the user's intent (LLM vs ML agent)."""
    prompt = prompt.lower().strip()

    # 🔹 JOB RECOMMENDATION INTENT
    job_keywords = [
        "job", "jobs", "recommendation", "recommendations",
        "top job", "top jobs", "best job",
        "suggest job", "suggest me job",
        "which job", "job role",
        "my top job", "find job"
    ]

    if any(k in prompt for k in ["take test", "start test", "i want to take", "give me the test", "start the", "take the","test","test for me"]):
        if "aptitude" in prompt:
            return "test:aptitude"
        if "communication" in prompt or "communicat" in prompt:
            return "test:communication"
        if "coding" in prompt or "code" in prompt or "programming" in prompt:
            return "test:coding"
        if "creativity" in prompt or "creative" in prompt or "story" in prompt:
            return "test:creativity"
        # fallback: let user choose
        return "test:choose"

    if any(k in prompt for k in job_keywords):
        print("🎯 Detected JOB intent")
        return "job"

    # 🔹 Career exploration
    if any(k in prompt for k in ["career", "profession", "scope", "salary","about","about career","career path"]):
        return "career"

    # 🔹 Roadmap
    elif any(k in prompt for k in ["roadmap", "steps", "plan", "path","Plan","Path","Steps","steps to","road map","step-by-step","step by step"]):
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

def run_llm_agent(agent_key: str, prompt: str):
    """Run LLM-based agent depending on key, and return formatted HTML."""
    mod = importlib.import_module(LLM_AGENTS.get(agent_key))

    try:
        if agent_key == "career":
            # ✅ Returns formatted career card
            html = mod.get_career_info(prompt)
            return Markup(html)

        elif agent_key == "roadmap":
            # ✅ Returns roadmap (already Markup formatted)
            html = mod.get_roadmap(prompt, {"DSA": 8, "Math": 7}, weeks=10)
            return Markup(html)

        elif agent_key == "linkedin":
            # 🧠 Text output, keep plain
            return mod.generate_linkedin_post(
                "AI",
                ["LLMs are transforming industry", "Focus on practical application"]
            )

        elif agent_key == "research":
            return mod.run_research(prompt)

        elif agent_key == "factcheck":
            return mod.fact_check(prompt)

        elif agent_key == "mooc":
            pdf_path = os.path.join(os.path.dirname(mod.__file__), "uu.pdf")
            return mod.run_pdf_mooc_query(prompt, pdf_path)

        else:
            return Markup(f"<p>⚠️ No valid LLM agent found for '<b>{agent_key}</b>'.</p>")

    except Exception as e:
        print(f"❌ Error in agent '{agent_key}':", e)
        return Markup(f"<p>⚠️ Error while running <b>{agent_key}</b> agent: {e}</p>")



# --------------------------------------------------
# RUN NON-LLM AGENTS

def run_non_llm_agent(agent_key: str, username=None, last_user_message=None):
    """Run non-LLM ML-based agents (job, subject, skills, etc.)."""
    # ---------------- JOB RECOMMENDATION ----------------
    if agent_key == "job":
        from agents.job_recommendation import get_job_recommendation_message
        username = username or "Guest"
        print(f"🚀 Running job recommendation for {username}...")

        try:
            html = get_job_recommendation_message(username)
            return Markup(html)
        except Exception as e:
            print("❌ Job recommendation failed:", e)
            return Markup(f"""
            <div style='padding:10px;background:#f8d7da;border-left:5px solid #dc3545;border-radius:6px;'>
                ⚠️ Sorry, I couldn’t fetch your job recommendations.<br>
                Error: {e}
            </div>
            """)



    elif agent_key == "skills":
        from agents.skill_profiler_agent import run_skill_profiler
        print("🎯 Running Skill Profiler...")
        profile = run_skill_profiler(username, "data/subjects.xlsx")
        return "✅ Skill profiler completed successfully."

    elif agent_key == "market":
        from agents.market_score_agent import MarketScoreAgent
        subject = None
        if isinstance(last_user_message, str):
        # Try extracting subject name from user query
            import re
            match = re.search(r"for\s+(.+)", last_user_message, re.IGNORECASE)
            if match:
                subject = match.group(1).strip()
        if not subject:
            subject = "Artificial Intelligence"  # Default fallback

        agent = MarketScoreAgent()
        return agent.get_score(subject)


    elif agent_key == "subject":
        import re
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
    prompt_lower = prompt.lower().strip()
    print("\n🧠 Classifying task type...")

    # ✅ 1. Detect test request ONLY if this prompt actually asks for a test
    if re.search(r"\b(take|start|begin|give|attempt|want).*\btest\b", prompt_lower):
        print("🎯 Detected explicit test request")
        return handle_test_request(prompt_lower)

    # ✅ 2. Normal flow (fresh classification each time)
    task_type = classify_prompt(prompt)

    if task_type == "unknown":
        return "⚠️ Sorry, I couldn’t determine what you’re asking about."

    # ✅ 3. Route normally to agents
    if task_type in LLM_AGENTS:
        print(f"🧩 Using LLM-based agent: {task_type}")
        result = run_llm_agent(task_type, prompt)
    elif task_type in NON_LLM_AGENTS:
        result = run_non_llm_agent(task_type, username, last_user_message)
    else:
        result = "❌ No suitable agent found."

    return result



def handle_test_request(prompt: str):
    """Respond with the appropriate test link based on user request."""
    prompt = prompt.lower().strip()

    # 🔍 Normalize to one word
    test_name = None
    route = None

    if "aptitude" in prompt:
        test_name, route = "Aptitude Test", "/aptitude_test"
    elif "communication" in prompt or "comm" in prompt:
        test_name, route = "Communication Test", "/communication_test"
    elif "creativity" in prompt or "creative" in prompt:
        test_name, route = "Creativity Test", "/creativity_test"
    elif "coding" in prompt or "programming" in prompt or "problem" in prompt:
        test_name, route = "Coding Test", "/coding_test"

    if not test_name:
        return Markup("""
        <div style='padding:10px;background:#fff3cd;border-left:5px solid #ffcc00;border-radius:8px;'>
          ⚠️ Please specify which test you'd like to take: 
          <b>Aptitude</b>, <b>Communication</b>, <b>Creativity</b>, or <b>Coding</b>.
        </div>
        """)

    # 🧠 Respond with a styled button
    return Markup(f"""
    <div style='padding:15px;background:#e3f2fd;border-left:5px solid #2196f3;border-radius:8px;'>
      Ready to begin your <b>{test_name}</b>?<br><br>
      <a href='{route}' target='_blank'>
        <button style='background:#007bff;color:white;border:none;padding:8px 16px;border-radius:5px;cursor:pointer;'>
          🚀 Start {test_name}
        </button>
      </a>
    </div>
    """)



# --------------------------------------------------
# TEST RUN (CLI MODE)
# --------------------------------------------------
if __name__ == "__main__":
    print("=== 🤖 Multi-Agent Orchestrator ===")
    user_prompt = input("Enter your query: ").strip()
    response = orchestrate(user_prompt, username="ss")
    print("\nResponse:\n", response)
