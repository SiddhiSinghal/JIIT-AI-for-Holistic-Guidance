# ==================== agents/roadmap.py ====================
import json
from markupsafe import Markup
from langchain_ollama import OllamaLLM
import re

# ✅ Initialize LLaMA 3 (optional, fallback available)
try:
    llm = OllamaLLM(model="llama3")
except Exception as e:
    print("⚠️ Ollama not found or model missing:", e)
    llm = None


def detect_context(user_message: str):
    """
    Detect if the user is asking about a job role or an academic subject/course.
    """
    job_keywords = [
        "developer", "engineer", "designer", "scientist", "manager",
        "analyst", "architect", "specialist", "consultant", "researcher",
        "tester", "intern", "administrator", "technician"
    ]
    course_keywords = [
        "subject", "course", "dbms", "dsa", "oop", "ai", "ml",
        "data structures", "python", "java", "iot", "network", "cloud"
    ]

    msg = user_message.lower()
    if any(word in msg for word in job_keywords):
        return "job"
    elif any(word in msg for word in course_keywords):
        return "course"
    else:
        return "unknown"


def generate_custom_roadmap(job_or_subject: str, topics: list, days: int = 30):
    """
    Generate a detailed roadmap for either a job or a course,
    with exactly {days} days total duration.
    """

    context_type = detect_context(job_or_subject)
    title_label = "Career Roadmap" if context_type == "job" else "Learning Roadmap"
    job_or_subject = job_or_subject.strip().title()
    topics_text = ", ".join(topics) if topics else "Core fundamentals"

    roadmap = None

    # 1️⃣ Try LLaMA 3 if available
    if llm:
        prompt = f"""
        You are a learning strategist.
        Create a structured roadmap for the {context_type} "{job_or_subject}"
        covering topics: {topics_text}. 
        Divide it logically across {days} days (must total exactly {days}).

        Include 5 steps. Each step must have:
        - "title": concise label
        - "task": what to learn or do
        - "days": integer (sum of all = {days})
        - "resources": 3 specific study or project URLs

        Output only valid JSON.
        """
        try:
            response = llm.invoke(prompt)
            roadmap = json.loads(response)
        except Exception as e:
            print("⚠️ LLaMA failed:", e)
            roadmap = None

    # 2️⃣ Fallback if LLaMA unavailable
    if not roadmap:
        pattern = [0.1, 0.2, 0.25, 0.25, 0.2]
        raw_days = [int(days * p) for p in pattern]
        diff = days - sum(raw_days)
        raw_days[-1] += diff

        if context_type == "job":
            step_titles = [
                "📘 Learn the Fundamentals",
                "🧩 Strengthen Core Concepts",
                "⚙️ Build Mini Projects",
                "🚀 Real-World Applications",
                "🎯 Final Prep & Portfolio"
            ]
        else:  # course/subject
            step_titles = [
                "📘 Understand the Basics",
                "📖 Deep Dive into Theory",
                "🧠 Solve Practice Questions",
                "💻 Implement Mini Projects",
                "🧾 Revise & Test Yourself"
            ]

        roadmap = {}
        for i, (title, step_days) in enumerate(zip(step_titles, raw_days)):
            if i == 0:
                task = f"Start with basic {job_or_subject} fundamentals. Focus on understanding key {topics_text} concepts."
                resources = [
                    f"https://www.youtube.com/results?search_query={job_or_subject.replace(' ', '+')}+basics",
                    f"https://www.coursera.org/search?query={job_or_subject.replace(' ', '%20')}",
                    f"https://www.geeksforgeeks.org/"
                ]
            elif i == 1:
                task = f"Explore advanced topics and strengthen your understanding of {topics_text} through tutorials and notes."
                resources = [
                    f"https://www.udemy.com/courses/search/?q=advanced+{job_or_subject.replace(' ', '%20')}",
                    f"https://www.freecodecamp.org/",
                    f"https://www.javatpoint.com/"
                ]
            elif i == 2:
                task = f"Apply your learnings by solving exercises or coding problems from {topics_text}."
                resources = [
                    f"https://leetcode.com/problemset/all/",
                    f"https://www.hackerrank.com/domains/tutorials/10-days-of-{job_or_subject.replace(' ', '-')}",
                    f"https://www.interviewbit.com/"
                ]
            elif i == 3:
                task = f"Work on small real-world projects to strengthen your practical grasp of {topics_text}."
                resources = [
                    f"https://github.com/topics/{job_or_subject.replace(' ', '-')}-projects",
                    f"https://www.kaggle.com/learn",
                    f"https://devpost.com/hackathons"
                ]
            else:
                task = f"Review all {topics_text} concepts, revise notes, and prepare a short summary or presentation."
                resources = [
                    f"https://www.notion.so/",
                    f"https://www.youtube.com/results?search_query={job_or_subject.replace(' ', '+')}+revision",
                    f"https://www.linkedin.com/learning/search?keywords={job_or_subject.replace(' ', '%20')}"
                ]

            roadmap[f"step_{i+1}"] = {
                "title": title,
                "task": task,
                "days": step_days,
                "resources": resources
            }

    # 3️⃣ HTML formatting
    html = f"<b>📘 {days}-Day {title_label} for {job_or_subject}</b><br><br>"
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

    html += "<br>✨ Stay consistent — follow each step with discipline!"
    return Markup(html)
