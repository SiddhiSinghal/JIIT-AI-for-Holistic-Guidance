# agents/linkedin_post_generator.py
import os
from dotenv import load_dotenv
import ollama

load_dotenv()

# model name is configurable via env LLM_MODEL, default 'mistral'
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")

def generate_linkedin_post(domain: str, pointers: list[str]) -> str:
    """
    domain: short domain label (e.g., 'AI', 'marketing')
    pointers: list of bullet-point strings (key insights)
    returns final linkedin post text
    """
    bullet_points = '\n'.join(f"- {point.strip()}" for point in pointers)

    prompt = f"""
You are a professional LinkedIn content writer.

Write a compelling, human-like LinkedIn post based on the following:
Domain: {domain}

Key Points:
{bullet_points}

Guidelines:
- Total length: around 1100 to 1200 characters (not words)
- Tone: Professional and inspiring (no emojis or hashtags)
- Structure: 1–2 short paragraphs
- Start with a hook, end with insight or reflection
- Do not use bullet points in the output
"""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response['message']['content']
