# agents/career_exploration.py
import json
from markupsafe import Markup

# ✅ Local LLaMA 3 (no key needed)
from langchain_ollama import OllamaLLM

# Try initializing LLaMA 3 locally
try:
    llm = OllamaLLM(model="llama3")
except Exception as e:
    print("⚠️ Ollama not found or model missing:", e)
    llm = None


def get_career_info(career_name: str):
    """
    Generate a styled HTML career overview for a given role.
    Matches roadmap.py styling — clean, modern, and consistent.
    """
    career_name = career_name.strip().title()
    if not career_name:
        return Markup("<p style='color:#999;'>⚠️ Please specify a career name.</p>")

    data = None

    # 1️⃣ Try using LLaMA 3 to get structured JSON
    if llm:
        prompt = f"""
        You are a professional career counselor.
        Provide structured, concise, and factual information about the career role '{career_name}'.

        Return ONLY valid JSON in this format:
        {{
          "title": "Software Engineer",
          "description": "Software Engineers design, build, and maintain software systems...",
          "skills": ["Programming", "Problem Solving", "Version Control"],
          "responsibilities": ["Develop software", "Collaborate with teams", "Optimize performance"],
          "education": "Bachelor’s degree in Computer Science or related field",
          "salary": "Depends on region and experience",
          "outlook": "High demand across industries"
        }}
        """
        try:
            response = llm.invoke(prompt)
            data = json.loads(response)
        except json.JSONDecodeError:
            print("⚠️ LLaMA output not JSON — using fallback.")
            data = None
        except Exception as e:
            print("⚠️ Error invoking LLaMA:", e)
            data = None

    # 2️⃣ Fallback structured data
    if not data:
        data = {
            "title": career_name,
            "description": f"{career_name} is a role that blends technical expertise, creativity, and problem-solving to deliver impactful outcomes.",
            "skills": ["Analytical Thinking", "Communication", "Adaptability"],
            "responsibilities": ["Work on projects", "Collaborate with teams", "Apply innovative solutions"],
            "education": "Bachelor’s degree or equivalent practical experience",
            "salary": "Varies by experience and company",
            "outlook": "Promising career growth opportunities"
        }

    # 3️⃣ Match roadmap-style formatted HTML
    html = f"""
    <b>💼 Career Overview: {data['title']}</b><br><br>
    <div style='margin-bottom:15px;padding:12px;background:#f8f9fa;
                border-left:5px solid #007bff;border-radius:6px;'>
        <p style='color:#333;margin-bottom:10px;'>{data['description']}</p>

        <span style='color:#0056b3;'><b>🔧 Key Skills:</b></span>
        <ul style='margin-top:6px;margin-bottom:10px;'>
            {''.join(f"<li>{s}</li>" for s in data.get('skills', []))}
        </ul>

        <span style='color:#0056b3;'><b>📋 Responsibilities:</b></span>
        <ul style='margin-top:6px;margin-bottom:10px;'>
            {''.join(f"<li>{r}</li>" for r in data.get('responsibilities', []))}
        </ul>

        <span style='color:#0056b3;'><b>🎓 Education:</b></span>
        <p style='margin-left:10px;margin-bottom:10px;'>{data.get('education', '')}</p>

        <span style='color:#0056b3;'><b>💰 Salary:</b></span>
        <p style='margin-left:10px;margin-bottom:10px;'>{data.get('salary', '')}</p>

        <span style='color:#0056b3;'><b>📈 Outlook:</b></span>
        <p style='margin-left:10px;margin-bottom:0;'>{data.get('outlook', '')}</p>
    </div>
    """

    return Markup(html)


# 🧩 Local test
if __name__ == "__main__":
    html = get_career_info("Full Stack Developer")
    print(html)
