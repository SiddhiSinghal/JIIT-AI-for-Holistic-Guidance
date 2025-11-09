# ==================== agents/roadmap.py ====================
import json
from markupsafe import Markup
from langchain_ollama import OllamaLLM

# ✅ Initialize LLaMA 3 (offline, no key needed)
try:
    llm = OllamaLLM(model="llama3")
except Exception as e:
    print("⚠️ Ollama not found or model missing:", e)
    llm = None


def generate_custom_roadmap(job_role: str, topics: list, days: int = 30):
    """
    Generate a detailed, progressive roadmap for a job role with exact total days.
    Steps evolve logically from basics to mastery — no repetition.
    """
    job_role = job_role.strip().title()
    topics_text = ", ".join(topics) if topics else "Core fundamentals"

    roadmap = None

    # 1️⃣ Try LLaMA 3 for structured roadmap (if running)
    if llm:
        prompt = f"""
        You are a professional career mentor.
        Create a 5-step roadmap to become a '{job_role}' focused on these topics: {topics_text}.
        The roadmap should progress clearly — starting from basics and ending at mastery.

        Total duration = {days} days (must add up exactly).
        Each step should include:
          - "task": brief, action-based task description
          - "days": integer number of days for that step
          - "resources": 3 URLs (Coursera, Udemy, YouTube)

        Return valid JSON only.
        """
        try:
            response = llm.invoke(prompt)
            roadmap = json.loads(response)
        except json.JSONDecodeError:
            roadmap = None
        except Exception as e:
            print("⚠️ LLaMA Error:", e)
            roadmap = None

    # 2️⃣ Fallback Dynamic Generation (if LLaMA not available or fails)
    if not roadmap:
        # Proportional step distribution (learning curve)
        pattern = [0.1, 0.2, 0.25, 0.25, 0.2]
        raw_days = [int(days * p) for p in pattern]
        diff = days - sum(raw_days)
        raw_days[-1] += diff

        # Define step themes for progression
        step_titles = [
            "📘 Learn the Fundamentals",
            "🧩 Strengthen Core Concepts",
            "⚙️ Apply through Mini Projects",
            "🚀 Work on Real-World Applications",
            "🎯 Final Revision & Portfolio Building"
        ]

        roadmap = {}
        for i, (title, step_days) in enumerate(zip(step_titles, raw_days)):
            if i == 0:
                task = f"Understand the fundamentals of {topics_text}. Learn key {job_role} basics like syntax, logic, and foundational theory."
                resources = [
                    f"https://www.youtube.com/results?search_query={job_role.replace(' ', '+')}+basics",
                    f"https://www.coursera.org/search?query={job_role.replace(' ', '%20')}+for+beginners",
                    f"https://www.w3schools.com/"
                ]
            elif i == 1:
                task = f"Dive deeper into intermediate {job_role} concepts — master {topics_text} through exercises and guided tutorials."
                resources = [
                    f"https://www.udemy.com/courses/search/?q=advanced+{job_role.replace(' ', '%20')}",
                    f"https://www.geeksforgeeks.org/",
                    f"https://www.freecodecamp.org/"
                ]
            elif i == 2:
                task = f"Start hands-on practice! Create 2–3 mini projects using {topics_text}."
                resources = [
                    f"https://github.com/topics/{job_role.replace(' ', '-')}-projects",
                    f"https://www.youtube.com/results?search_query={job_role.replace(' ', '+')}+projects",
                    f"https://www.kaggle.com/learn"
                ]
            elif i == 3:
                task = f"Apply your skills to real-world problems — build full projects or participate in online hackathons related to {job_role}."
                resources = [
                    f"https://www.hackerrank.com/domains/tutorials/10-days-of-{job_role.replace(' ', '-')}",
                    f"https://devpost.com/hackathons",
                    f"https://www.coursera.org/projects"
                ]
            else:
                task = f"Polish your portfolio — document your projects, prepare for interviews, and revise {topics_text} for confidence."
                resources = [
                    f"https://leetcode.com/",
                    f"https://www.interviewbit.com/",
                    f"https://www.linkedin.com/learning/search?keywords={job_role.replace(' ', '%20')}"
                ]

            roadmap[f"step_{i+1}"] = {
                "title": title,
                "task": task,
                "days": step_days,
                "resources": resources
            }

    # 3️⃣ Format HTML (clean, styled, non-repetitive)
    html = f"<b>📘 {days}-Day Roadmap to Become a {job_role}</b><br><br>"
    for i, details in enumerate(roadmap.values(), start=1):
        title = details.get("title", f"Step {i}")
        task = details.get("task", "")
        step_days = details.get("days", 1)
        resources = details.get("resources", [])
        html += f"""
        <div style='margin-bottom:15px;padding:12px;background:#f8f9fa;
                    border-left:5px solid #007bff;border-radius:6px;'>
            <b>{title}</b><br>
            <p style='margin:5px 0;color:#333;'>{task}</p>
            <span style='color:#555;'>⏱ Duration: {step_days} day{'s' if step_days > 1 else ''}</span><br>
            <span style='color:#333;'>📚 Resources:</span>
            <ul style='margin-top:6px;margin-bottom:0;'>"""
        for r in resources:
            html += f"<li><a href='{r}' target='_blank'>{r}</a></li>"
        html += "</ul></div>"

    html += "<br>✨ Stay consistent — follow each step to master your journey!"
    return Markup(html)
