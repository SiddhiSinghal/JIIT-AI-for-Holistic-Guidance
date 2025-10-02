# orchestrator.py
from agents import career_exploration, roadmap, job_recommendation

def dict_to_string(d):
    """Convert dict to readable string for chat"""
    if not isinstance(d, dict):
        return str(d)
    text = ""
    for k, v in d.items():
        if isinstance(v, list):
            v = ", ".join(map(str, v))
        text += f"{k.capitalize()}: {v}\n"
    return text

def decide_and_call(message: str, user_scores=None):
    m = message.lower().strip()

    # Career exploration
    if "tell me about" in m or m.startswith("career"):
        parts = message.split("about", 1)
        target = parts[1].strip() if len(parts) > 1 else message
        info = career_exploration.get_career_info(target)
        payload = dict_to_string(info)
        return {"type": "career", "payload": payload}

    # Roadmap
    if "how to become" in m or "roadmap" in m or "plan to become" in m or m.startswith("how to"):
        for phrase in ["how to become", "roadmap to become", "roadmap for", "how to"]:
            if phrase in m:
                role = m.split(phrase,1)[1].strip()
                break
        else:
            role = message
        info = roadmap.get_roadmap(role, user_scores or {}, weeks=10)
        payload = dict_to_string(info) if isinstance(info, dict) else str(info)
        return {"type": "roadmap", "payload": payload}

    # Job recommendation
    if "recommend" in m or "suggest job" in m or "which job" in m or "job for me" in m:
        vals = None
        if isinstance(user_scores, dict):
            order = ['DSA','DBMS','OS','CN','Mathmetics','Aptitute','Comm','Problem_Solving','Creative','Hackathons']
            vals = [user_scores.get(k,0) for k in order]
        else:
            vals = [50]*10
        payload = job_recommendation.predict_jobs_from_list(vals)
        payload = dict_to_string(payload) if isinstance(payload, dict) else str(payload)
        return {"type": "job_recommendation", "payload": payload}

    # fallback
    return {"type": "unknown", "payload": "Sorry, I couldn't understand. Try asking 'Tell me about Data Scientist' or 'How to become Data Scientist' or 'Give me job recommendation'."}
