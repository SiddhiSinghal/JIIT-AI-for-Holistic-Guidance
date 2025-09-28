# test/test_prompt_classifier.py

import sys
import os

# Ensure project root is on sys.path so top-level packages like `agents` can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prompt_classifier_agent import PromptClassifierAgent

classifier = PromptClassifierAgent()

prompts = [
    "Recommend me electives for next semester",
    "Show my skill profile",
    "Help me understand the system",
    "What is AI?"
]

for p in prompts:
    result = classifier.classify(p)
    print(f"Prompt: {p} -> Intent: {result['intent']}")
