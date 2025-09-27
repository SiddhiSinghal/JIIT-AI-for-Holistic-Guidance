# agents/aptitude_test.py
import json, random, os

DEFAULT_FILE = "aptitude_questions.json"

def load_questions(file_path=DEFAULT_FILE):
    if not os.path.exists(file_path):
        # small defaults
        return [
            {"id":"q1","question":"2+2","answer":"4"},
            {"id":"q2","question":"5*6","answer":"30"},
            {"id":"q3","question":"Square root of 16","answer":"4"}
        ]
    with open(file_path, "r") as f:
        return json.load(f)

def get_random_questions(n=10):
    questions = load_questions()
    if len(questions) <= n:
        return questions
    return random.sample(questions, n)
