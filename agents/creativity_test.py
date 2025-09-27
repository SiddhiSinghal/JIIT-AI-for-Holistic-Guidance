# agents/creativity_test.py
import re, random

PROMPTS = [
    "Write a story about a world where dreams come true.",
    "Describe a day in the life of a time traveler.",
    "A mysterious door appears in your house. What happens next?"
]

def get_prompt():
    return random.choice(PROMPTS)

def _check_grammar(story):
    return len(re.findall(r'\b(is|are|was|were)\s+a\b', story, re.IGNORECASE))

def _assess_creativity(story):
    unique_words = len(set(story.split()))
    return min(10, unique_words // 10)

def _assess_coherence(story):
    sentences = re.split(r'[.!?]', story)
    return min(10, len(set(sentences)) // 5)

def _assess_engagement(story):
    sentences = re.split(r'[.!?]', story)
    return min(10, (len(story.split()) + len(set(sentences))) // 20)

def get_feedback(story):
    score = (_assess_creativity(story) + _assess_coherence(story) + (10 - _check_grammar(story)) + _assess_engagement(story)) / 4
    return (f"Overall Score: {score:.2f}/10", score)
