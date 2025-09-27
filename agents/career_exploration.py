# agents/career_exploration.py
import os, json
from dotenv import load_dotenv
load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_KEY)

def get_career_info(career_name: str):
    """
    Returns a dict with keys: title, description, skills, responsibilities, education, salary, outlook
    Falls back to canned response if no OpenAI key
    """
    career_name = career_name.strip()
    if not career_name:
        return {"title": "", "description": "No career specified.", "skills": [], "responsibilities": [], "education": "", "salary": "", "outlook": ""}

    if OPENAI_KEY:
        prompt = f"""
Provide detailed information about the job role '{career_name}' in JSON format with keys:
"title","description","skills","responsibilities","education","salary","outlook".
Make it professional and concise.
"""
        try:
            resp = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role":"system","content":"You are a career guidance expert."},
                          {"role":"user","content":prompt}],
                temperature=0.3,
                max_tokens=800
            )
            content = resp.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print("OpenAI error:", e)
    # fallback canned
    return {
        "title": career_name,
        "description": f"{career_name} is a role that requires domain knowledge, problem solving and communication skills.",
        "skills": ["Core domain skills", "Problem solving", "Communication"],
        "responsibilities": ["Design solutions", "Collaborate with team"],
        "education": "Relevant degree or self-taught experience",
        "salary": "Varies by region",
        "outlook": "Good"
    }
