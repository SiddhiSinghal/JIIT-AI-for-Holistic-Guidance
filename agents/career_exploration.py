# agents/career_exploration.py
import json
from markupsafe import Markup

# ✅ Modern Ollama import (no API key needed)
from langchain_ollama import OllamaLLM

# Initialize LLaMA 3 model safely
try:
    llm = OllamaLLM(model="llama3")
except Exception as e:
    print("⚠️ Ollama not found or model missing:", e)
    llm = None


def get_career_info(career_name: str):
    """
    Returns formatted HTML about a career — similar visual format as roadmap.py
    Uses LLaMA 3 via Ollama (offline, no key required).
    """
    career_name = career_name.strip().title()
    if not career_name:
        return Markup("<p style='color:#999;'>⚠️ Please specify a career name.</p>")

    data = None

    # 1️⃣ Try generating structured JSON using LLaMA 3
    if llm:
        prompt = f"""
        You are a career counseling expert.
        Provide accurate and professional information about the role '{career_name}'.

        Return ONLY valid JSON in this format:
        {{
          "title": "Software Engineer",
          "description": "Software Engineers design, develop, and maintain software applications...",
          "skills": ["Programming", "Problem Solving", "Version Control"],
          "responsibilities": ["Develop software", "Collaborate with teams", "Debug and optimize code"],
          "education": "Bachelor’s degree in Computer Science or equivalent experience",
          "salary": "Typical range depends on region and experience",
          "outlook": "High demand across technology industries"
        }}
        """
        try:
            response = llm.invoke(prompt)
            data = json.loads(response)
        except json.JSONDecodeError:
            print("⚠️ LLaMA output not JSON — using fallback structure.")
            data = {
                "title": career_name,
                "description": response.strip()[:500],
                "skills": ["Analytical Thinking", "Team Collaboration"],
                "responsibilities": ["Perform duties relevant to the field"],
                "education": "Relevant degree or certification",
                "salary": "Depends on experience",
                "outlook": "Positive"
            }
        except Exception as e:
            print("⚠️ LLaMA error:", e)
            data = None

    # 2️⃣ Fallback static data if no model available
    if not data:
        data = {
            "title": career_name,
            "description": f"{career_name} is a dynamic role that requires technical skills, problem-solving ability, and adaptability in fast-paced environments.",
            "skills": ["Problem Solving", "Communication", "Adaptability"],
            "responsibilities": ["Work on practical projects", "Collaborate with teams", "Deliver impactful results"],
            "education": "Bachelor’s degree or equivalent industry experience",
            "salary": "Varies by region and seniority",
            "outlook": "Strong career growth expected"
        }

    # 3️⃣ Beautiful formatted HTML (matching roadmap style)
    html = f"""
    <div style='margin-bottom:20px;padding:15px;background:#f8f9fa;
                border-left:5px solid #007bff;border-radius:8px;'>
        <h4 style='color:#007bff;margin-bottom:8px;'>💼 {data['title']}</h4>
        <p style='color:#333;margin-bottom:12px;'>{data['description']}</p>

        <div style='margin-top:10px;'>
            <h6 style='color:#0056b3;'>🔧 Key Skills</h6>
            <ul style='margin-left:20px;margin-bottom:10px;'>
                {''.join(f"<li>{s}</li>" for s in data.get('skills', []))}
            </ul>

            <h6 style='color:#0056b3;'>📋 Responsibilities</h6>
            <ul style='margin-left:20px;margin-bottom:10px;'>
                {''.join(f"<li>{r}</li>" for r in data.get('responsibilities', []))}
            </ul>

            <h6 style='color:#0056b3;'>🎓 Education</h6>
            <p style='margin-left:10px;'>{data.get('education', '')}</p>

            <h6 style='color:#0056b3;'>💰 Salary</h6>
            <p style='margin-left:10px;'>{data.get('salary', '')}</p>

            <h6 style='color:#0056b3;'>📈 Outlook</h6>
            <p style='margin-left:10px;'>{data.get('outlook', '')}</p>
        </div>
    </div>
    """

    return Markup(html)
