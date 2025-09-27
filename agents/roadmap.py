# agents/roadmap.py
import os, json
from dotenv import load_dotenv
load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_KEY)

def get_roadmap(job_role: str, user_scores: dict, weeks: int = 10):
    job_role = job_role.strip()
    score_summary = "\n".join([f"{k}: {v}" for k,v in user_scores.items()]) if user_scores else "No scores provided."
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
                messages=[{"role":"system","content":"You are an assistant that outputs only JSON roadmaps."},
                          {"role":"user","content":prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            content = resp.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print("OpenAI error:", e)
    # fallback heuristic roadmap
    per_step = max(1, weeks // 5)
    roadmap = {}
    for i in range(5):
        roadmap[f"step_{i+1}"] = {
            "task": f"Step {i+1}: Learn/practice {job_role}-related topics.",
            "weeks": per_step,
            "resources": [f"{job_role} resource {i+1}-1", f"{job_role} resource {i+1}-2", f"{job_role} resource {i+1}-3"]
        }
    # adjust last step weeks to make sum equal
    total = per_step*5
    if total != weeks:
        diff = weeks - total
        roadmap["step_5"]["weeks"] += diff
    return roadmap
