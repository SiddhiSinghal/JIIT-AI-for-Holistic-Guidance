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


# -----------------------------------------------------
# ROLE NAME CLEANER
# -----------------------------------------------------
def extract_role_name(prompt: str):
    """
    Extract clean career role name.
    Example:
      'Tell me about career in AI' → 'AI'
      'What is the salary of a data scientist?' → 'Data Scientist'
    """
    import re

    remove_words = r"\b(what|is|the|a|an|about|tell|me|career|in|of|on|for|salary|path|scope|role)\b"
    cleaned = re.sub(remove_words, "", prompt, flags=re.I)

    # Remove punctuation
    cleaned = re.sub(r"[^\w\s]", "", cleaned)

    cleaned = cleaned.strip()
    return cleaned if cleaned else prompt.strip()


# -----------------------------------------------------
# FALLBACK CAREER DATABASE
# -----------------------------------------------------
FALLBACK_DB = {
    "Ai": {
        "title": "AI Engineer",
        "description": "AI Engineers build intelligent systems, machine learning models, and automation frameworks.",
        "skills": ["Python", "Machine Learning", "Deep Learning", "Data Structures", "MLOps"],
        "responsibilities": [
            "Develop and optimize ML models",
            "Build AI systems",
            "Deploy ML pipelines",
            "Research new AI techniques"
        ],
        "education": "B.Tech in CSE / AI / ML or equivalent practical experience",
        "salary": "₹8–30 LPA in India depending on company and experience",
        "outlook": "Explosive demand globally, especially 2024–2030"
    },

    "Data Scientist": {
        "title": "Data Scientist",
        "description": "Data Scientists analyze data, build predictive models, and generate insights to drive decisions.",
        "skills": ["Python", "Statistics", "Machine Learning", "SQL", "Data Visualization"],
        "responsibilities": [
            "Build ML models",
            "Clean and process data",
            "Feature engineering",
            "Create dashboards and reports"
        ],
        "education": "Bachelor’s or Master’s in Data Science, CS, Statistics, or equivalent",
        "salary": "₹10–40 LPA depending on seniority",
        "outlook": "Among the top 3 most in-demand roles worldwide"
    },

    "Software Engineer": {
        "title": "Software Engineer",
        "description": "Software Engineers design, build, test, and maintain applications and systems.",
        "skills": ["DSA", "OOP", "System Design", "Databases", "Problem-Solving"],
        "responsibilities": [
            "Write clean and scalable code",
            "Design system components",
            "Collaborate with product teams",
            "Optimize performance"
        ],
        "education": "Bachelor’s degree in Computer Science or related field",
        "salary": "₹8–45 LPA depending on company",
        "outlook": "Evergreen demand across all tech sectors"
    }
}


# -----------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------
def get_career_info(career_name: str):
    """
    Generate a styled HTML career overview for a given role.
    Supports structured JSON from LLaMA, with strong fallbacks.
    """

    # Extract real role name
    cleaned_role = extract_role_name(career_name)
    cleaned_role = cleaned_role.strip().title()

    if not cleaned_role:
        return Markup("<p style='color:#999;'>⚠️ Please specify a career name.</p>")

    data = None

    # -------------------------------------------------
    # 1️⃣ Try using LLaMA to get structured JSON
    # -------------------------------------------------
    if llm:
        prompt = f"""
        You are a professional career counselor.
        Provide structured, concise, and factual information about the career role '{cleaned_role}'.

        Return ONLY valid JSON in this format:
        {{
          "title": "",
          "description": "",
          "skills": [],
          "responsibilities": [],
          "education": "",
          "salary": "",
          "outlook": ""
        }}
        """
        try:
            response = llm.invoke(prompt)

            # Extract JSON safely
            import re
            json_match = re.search(r"\{.*\}", response, re.S)

            if json_match:
                data = json.loads(json_match.group(0))
            else:
                print("⚠️ Could not extract JSON — using fallback.")
                data = None

        except Exception as e:
            print("⚠️ Error invoking LLaMA / JSON parse:", e)
            data = None

    # -------------------------------------------------
    # 2️⃣ Fallback database
    # -------------------------------------------------
    if not data:
        data = FALLBACK_DB.get(
            cleaned_role,
            {   # Default generic fallback
                "title": cleaned_role,
                "description": f"{cleaned_role} is a professional role requiring domain-specific expertise.",
                "skills": ["Analytical Thinking", "Communication"],
                "responsibilities": ["Work on projects", "Collaborate with teams"],
                "education": "Bachelor’s degree or equivalent experience",
                "salary": "Depends on experience, company, and region",
                "outlook": "Promising career growth opportunities"
            }
        )

    # -------------------------------------------------
    # 3️⃣ Generate HTML Output
    # -------------------------------------------------
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