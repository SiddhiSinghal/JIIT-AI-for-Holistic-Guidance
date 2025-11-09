# agents/roadmap.py
import json
from markupsafe import Markup

# ✅ Modern Ollama import (no API key needed)
from langchain_ollama import OllamaLLM

# Try initializing LLaMA 3 locally
try:
    llm = OllamaLLM(model="llama3")
except Exception as e:
    print("⚠️ Ollama not found or model missing:", e)
    llm = None


def get_roadmap(job_role: str, user_scores: dict, weeks: int = 10):
    """Generate and format a 5-step roadmap for a given job role (offline, LLaMA 3)."""
    job_role = job_role.strip().title()
    score_summary = "\n".join([f"{k}: {v}" for k, v in user_scores.items()]) if user_scores else "No scores provided."

    roadmap = None

    # 1️⃣ Use LLaMA 3 if available
    if llm:
        prompt = f"""
        You are an expert career counselor.
        Student profile scores:
        {score_summary}

        Create a 5-step learning roadmap to become a '{job_role}' in {weeks} weeks.

        Return ONLY valid JSON with this structure:
        {{
          "step_1": {{"task": "", "weeks": 1, "resources": ["", "", ""]}},
          "step_2": {{"task": "", "weeks": 2, "resources": ["", "", ""]}},
          ...
          "step_5": {{"task": "", "weeks": 3, "resources": ["", "", ""]}}
        }}
        Make sure the total weeks equal {weeks}.
        """
        try:
            response = llm.invoke(prompt)
            roadmap = json.loads(response)
        except json.JSONDecodeError:
            # If LLaMA output isn't JSON, fall back to a heuristic roadmap
            print("⚠️ LLaMA output not valid JSON — using fallback roadmap.")
            roadmap = None
        except Exception as e:
            print("⚠️ Error invoking LLaMA:", e)
            roadmap = None

    # 2️⃣ Fallback static roadmap if no LLM or bad output
    if not roadmap:
        per_step = max(1, weeks // 5)
        roadmap = {}
        for i in range(5):
            roadmap[f"step_{i+1}"] = {
                "task": f"Step {i+1}: Learn/practice {job_role}-related topics.",
                "weeks": per_step,
                "resources": [
                    f"https://www.coursera.org/search?query={job_role.replace(' ', '%20')}",
                    f"https://www.udemy.com/courses/search/?q={job_role.replace(' ', '%20')}",
                    f"https://www.youtube.com/results?search_query={job_role.replace(' ', '+')}"
                ]
            }
        total = per_step * 5
        if total != weeks:
            roadmap["step_5"]["weeks"] += (weeks - total)

    # 3️⃣ Format into styled HTML
    html = f"<b>📘 Roadmap to Become a {job_role}</b><br><br>"
    for i, (step, details) in enumerate(roadmap.items(), start=1):
        task = details.get("task", "")
        step_weeks = details.get("weeks", 1)
        resources = details.get("resources", [])
        html += f"""
        <div style='margin-bottom:15px;padding:12px;background:#f8f9fa;
                    border-left:5px solid #007bff;border-radius:6px;'>
            <b>Step {i}:</b> {task}<br>
            <span style='color:#555;'>⏱ Duration: {step_weeks} week{'s' if step_weeks > 1 else ''}</span><br>
            <span style='color:#333;'>📚 Resources:</span>
            <ul style='margin-top:6px;margin-bottom:0;'>"""
        for r in resources:
            html += f"<li><a href='{r}' target='_blank'>{r}</a></li>"
        html += "</ul></div>"
    html += "<br>✨ Stay consistent — each step brings you closer to your goal!"

    return Markup(html)

