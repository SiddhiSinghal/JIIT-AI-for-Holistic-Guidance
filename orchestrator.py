# orchestrator.py
from agents import (
    career_exploration,
    roadmap,
    job_recommendation,
    coding_test,
    aptitude_test,
    creativity_test,
    communication_test
)

def decide_and_call(message: str, user_scores=None):
    """
    message: user input string
    user_scores: dict or None
    Returns: dict with keys: 'type' and 'payload' (payload can be dict or string)
    """
    m = message.lower().strip()

    # Career exploration
    if m.startswith("tell me about") or "tell me about" in m or m.startswith("career") or "career" in m:
        # parse the career name
        parts = message.split("about", 1)
        target = parts[1].strip() if len(parts) > 1 else message
        payload = career_exploration.get_career_info(target)
        return {"type": "career", "payload": payload}

    # Roadmap
    if "how to become" in m or "roadmap" in m or "plan to become" in m or m.startswith("how to"):
        # extract role
        for phrase in ["how to become", "roadmap to become", "roadmap for", "how to"]:
            if phrase in m:
                role = m.split(phrase,1)[1].strip()
                break
        else:
            role = message
        payload = roadmap.get_roadmap(role, user_scores or {}, weeks=10)
        return {"type": "roadmap", "payload": payload}

    # Job recommendation
    if "recommend" in m or "suggest job" in m or "which job" in m or "job for me" in m:
        # build list
        vals = None
        if isinstance(user_scores, dict):
            # convert to list in expected order
            order = ['DSA','DBMS','OS','CN','Mathmetics','Aptitute','Comm','Problem_Solving','Creative','Hackathons']
            vals = [user_scores.get(k,0) for k in order]
        else:
            vals = [50]*10
        payload = job_recommendation.predict_jobs_from_list(vals)
        return {"type": "job_recommendation", "payload": payload}

    # Coding
    if "coding" in m or "program" in m or "challenge" in m or "coding question" in m:
        q = coding_test.get_random_question()
        return {"type": "coding_question", "payload": {"question": q}}

    # Aptitude
    if "aptitude" in m or "aptitude question" in m or "test" in m:
        qlist = aptitude_test.get_random_questions(n=5)
        return {"type": "aptitude", "payload": qlist}

    # Creativity
    if m.startswith("creativity:") or "creativity" in m or "write a story" in m:
        prompt = creativity_test.get_prompt()
        return {"type": "creativity_prompt", "payload": {"prompt": prompt}}

    # Communication
    if "communication" in m or "assess my" in m or m.startswith("communication:"):
        return {"type": "communication_prompt", "payload": {"prompt": "Write a short paragraph or email for assessment."}}

    # fallback
    return {"type": "unknown", "payload": "Sorry, I couldn't understand. Try asking 'Tell me about Data Scientist' or 'How to become Data Scientist' or 'Give me a coding question'."}
