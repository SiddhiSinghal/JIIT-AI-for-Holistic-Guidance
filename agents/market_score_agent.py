# agents/market_score_agent.py

import sys
import os

# Ensure project root is on sys.path so top-level packages like `agents` can be imported
#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.ai_utils import get_subject_market_score

def interpret_market_score(score: float) -> str:
    """
    Provide a textual meaning for the market score.
    """
    if score >= 90:
        return "Excellent demand in the market. Highly recommended for career prospects."
    elif score >= 75:
        return "Strong demand in the market. Good opportunities available."
    elif score >= 60:
        return "Moderate demand. Some opportunities, consider carefully."
    elif score >= 45:
        return "Low demand. Limited opportunities; skill enhancement recommended."
    else:
        return "Very low demand. Consider alternative subjects or skills."

class MarketScoreAgent:
    def __init__(self):
        pass

    def get_score(self, subject_name: str) -> dict:
        """
        Compute market score for a given subject and provide interpretation.
        """
        score = get_subject_market_score(subject_name)
        meaning = interpret_market_score(score)
        return {
            "subject": subject_name,
            "market_score": score,
            "meaning": meaning
        }

# Example usage:
if __name__ == "__main__":
    agent = MarketScoreAgent()
    subject = "Neurology"
    result = agent.get_score(subject)
    # print(result)
