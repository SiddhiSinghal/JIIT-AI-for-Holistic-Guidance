# agents/prompt_classifier_agent.py

class PromptClassifierAgent:
    def __init__(self):
        # Define keywords for each intent
        self.rules = {
            "recommendation": ["recommend", "elective", "suggest", "next semester"],
            "profile": ["profile", "skills", "strength", "chart", "analyze"],
            "market": ["market", "demand", "scope", "trend", "job", "career"],
            "help": ["help", "guide", "instructions"]
        }

    def classify(self, prompt: str) -> dict:
        prompt_lower = prompt.lower()

        # Match based on rules
        for intent, keywords in self.rules.items():
            if any(word in prompt_lower for word in keywords):
                return {"intent": intent}

        # Default fallback
        return {"intent": "other"}
