# agents/roadmap.py
import os, json
from markupsafe import Markup
from dotenv import load_dotenv
load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_KEY)

def get_roadmap(job_role: str, user_scores: dict, weeks: int = 10):
    """Generate and format a 5-step roadmap for a given job role."""
    job_role = job_role.strip().title()
    score_summary = "\n".join([f"{k}: {v}" for k, v in user_scores.items()]) if user_scores else "No scores provided."

    roadmap = None
    if OPENAI_KEY:
        prompt = f"""
You are an expert career counselor.
Student scores:
{score_summary}

Generate a 5-step roadmap to become a '{job_role}' in {weeks} weeks.
Return JSON like:
{{"step_1":{{"task":"", "weeks":1, "resources":["","",""]}}, ... "step_5":{{...}}}}
Ensure the sum of weeks is {weeks}. Return only JSON.
"""
        try:
            resp = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an assistant that outputs only JSON roadmaps."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            content = resp.choices[0].message.content
            roadmap = json.loads(content)
        except Exception as e:
            print("⚠️ OpenAI error:", e)

    # fallback heuristic roadmap if API not available
    if not roadmap:
        per_step = max(1, weeks // 5)
        roadmap = {}
        for i in range(5):
            roadmap[f"step_{i+1}"] = {
                "task": f"Step {i+1}: Learn/practice {job_role}-related topics.",
                "weeks": per_step,
                "resources": [
                    f"{job_role} Resource {i+1}-1",
                    f"{job_role} Resource {i+1}-2",
                    f"{job_role} Resource {i+1}-3"
                ]
            }
        # Adjust last step to match week total
        total = per_step * 5
        if total != weeks:
            diff = weeks - total
            roadmap["step_5"]["weeks"] += diff

    # ✅ Format into HTML
    html = f"<b>🧭 Roadmap to Become a {job_role}</b><br><br>"
    for i, (step, details) in enumerate(roadmap.items(), start=1):
        task = details.get("task", "")
        step_weeks = details.get("weeks", 1)
        resources = details.get("resources", [])
        html += f"""
        <div style='margin-bottom:15px;padding:10px;background:#f8f9fa;border-left:4px solid #007bff;border-radius:6px;'>
            <b>🚀 Step {i}:</b> {task}<br>
            <span style='color:#555;'>⏱️ Duration: {step_weeks} week{'s' if step_weeks > 1 else ''}</span><br>
            <span style='color:#333;'>📚 Resources:</span><br>
            <ul style='margin-top:4px;margin-bottom:0;'>""" 
        for r in resources:
            html += f"<li><a href='{r}' target='_blank'>{r}</a></li>"
        html += "</ul></div>"
    html += "<br>✨ Stay consistent and keep building — each step brings you closer to your goal!"

    return Markup(html)
