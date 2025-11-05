import sys
import os
from markupsafe import Markup
from utils.ai_utils import get_subject_market_score

# --------------------------
# Helper: Interpret market score
# --------------------------
def interpret_market_score(score: float) -> str:
    """
    Provide a textual meaning for the market score.
    """
    if score >= 90:
        return "🌟 Excellent demand in the market. Highly recommended for career prospects."
    elif score >= 75:
        return "💼 Strong demand in the market. Great opportunities available."
    elif score >= 60:
        return "📈 Moderate demand. Some opportunities — consider carefully."
    elif score >= 45:
        return "⚠️ Low demand. Limited opportunities; skill enhancement recommended."
    else:
        return "🚫 Very low demand. Consider alternative subjects or upskilling."

# --------------------------
# Class: Market Score Agent
# --------------------------
class MarketScoreAgent:
    def __init__(self):
        pass

    def get_score(self, subject_name: str):
        """
        Compute and return formatted market score HTML for a subject.
        """
        if not subject_name or not isinstance(subject_name, str):
            return Markup("<b>⚠️ Please specify a valid subject name.</b>")

        try:
            score = get_subject_market_score(subject_name)
            meaning = interpret_market_score(score)

            # Create a nice HTML snippet for chat display
            html_response = f"""
            <div style='padding:10px;'>
                <b>📊 Market Demand Analysis</b><br><br>
                <b>Subject:</b> {subject_name.title()}<br>
                <b>Market Score:</b> {score:.1f}/100<br>
                <b>Interpretation:</b> {meaning}<br><br>
                <div style="background:#e0e0e0;border-radius:8px;height:10px;width:80%;margin-top:5px;">
                    <div style="width:{min(score,100)}%;background:#4CAF50;height:10px;border-radius:8px;"></div>
                </div>
            </div>
            """
            return Markup(html_response)

        except Exception as e:
            return Markup(f"<b>⚠️ Error fetching market score:</b> {str(e)}")


# --------------------------
# Example CLI test
# --------------------------
if __name__ == "__main__":
    agent = MarketScoreAgent()
    test_subjects = ["Artificial Intelligence", "Blockchain", "Neurology"]
    for subj in test_subjects:
        print(agent.get_score(subj))
