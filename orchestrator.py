# orchestrator.py
"""
Master orchestrator that:
- Classifies the prompt intent (PromptClassifierAgent)
- Decides whether to use Non-LLM or LLM agents (or both)
- Orchestrates non-LLM agents first to produce structured data
- Calls LLM agents that may use structured data to produce user-friendly output
- Returns a unified response dict suitable for the Flask/chat endpoint
"""

from typing import Any, Dict, Optional
import traceback

# Import agents (these are the files you provided)
from agents.prompt_classifier_agent import PromptClassifierAgent

# LLM agents
try:
    from agents import career_exploration, roadmap, fact_checker, web_researcher, linkedin_post_generator
except Exception:
    # If module import fails, we still continue with what's available
    career_exploration = None
    roadmap = None
    fact_checker = None
    web_researcher = None
    linkedin_post_generator = None

# Non-LLM agents
try:
    from agents import job_recommendation, market_score_agent, skill_profiler_agent, recommendation_agent
except Exception:
    job_recommendation = None
    market_score_agent = None
    skill_profiler_agent = None
    recommendation_agent = None

# ---- Helper utilities ----
def safe_call(fn, *args, **kwargs):
    """Call fn safely and return (success, result_or_error_str)."""
    if fn is None:
        return False, "Function or agent not available"
    try:
        return True, fn(*args, **kwargs)
    except Exception as e:
        tb = traceback.format_exc()
        return False, f"{repr(e)}\n{tb}"

def dict_to_string(d: Any) -> str:
    """Convert dict or list to readable string for chat."""
    if d is None:
        return ""
    if isinstance(d, str):
        return d
    if isinstance(d, list):
        try:
            return "\n".join(map(str, d))
        except Exception:
            return str(d)
    if isinstance(d, dict):
        parts = []
        for k, v in d.items():
            if isinstance(v, (list, tuple)):
                v = ", ".join(map(str, v))
            elif isinstance(v, dict):
                v = dict_to_string(v)
            parts.append(f"{k}: {v}")
        return "\n".join(parts)
    return str(d)

# ---- Orchestrators ----
class NonLLMOrchestrator:
    """
    Orchestrates non-LLM agents (models, rule-based, local analysis).
    Produces structured outputs that LLM agents can consume.
    """
    def __init__(self):
        # prompt classifier is rule-based (non-LLM)
        self.classifier = PromptClassifierAgent()

    def intent_from_prompt(self, prompt: str) -> Dict[str, Any]:
        return self.classifier.classify(prompt)

    def run_job_recommendation(self, user_scores: Optional[dict] = None):
        """
        Try to gather job recommendations from available functions:
        - prefer job_recommendation.recommend_jobs() if present
        - else try recommendation_agent.generate_recommendations or similar
        - else provide fallback
        """
        # 1) try job_recommendation.recommend_jobs()
        if job_recommendation is not None:
            if hasattr(job_recommendation, "recommend_jobs"):
                ok, result = safe_call(job_recommendation.recommend_jobs)
                if ok:
                    return {"source": "job_recommendation.recommend_jobs", "jobs": result}
            # some versions might expose different APIs
            if hasattr(job_recommendation, "predict_jobs_from_list"):
                try:
                    # attempt to build default list if user_scores not provided
                    if user_scores and isinstance(user_scores, dict):
                        # try to map to expected order if known
                        order = ['DSA','DBMS','OS','CN','Mathmetics','Aptitute','Comm','Problem_Solving','Creative','Hackathons']
                        vals = [user_scores.get(k,0) for k in order]
                    else:
                        vals = [50]*10
                    ok, result = safe_call(job_recommendation.predict_jobs_from_list, vals)
                    if ok:
                        return {"source": "job_recommendation.predict_jobs_from_list", "jobs": result}
                except Exception:
                    pass

        # 2) try recommendation_agent.generate_recommendations (returns dataframe)
        if recommendation_agent is not None and hasattr(recommendation_agent, "generate_recommendations"):
            try:
                # require args; best-effort: expect user has CSV/XLSX paths or we can't run here
                ok, result = safe_call(recommendation_agent.generate_recommendations, {}, None, 6)
                if ok:
                    return {"source": "recommendation_agent.generate_recommendations", "jobs": result}
            except Exception:
                pass

        # fallback
        return {"source": "fallback", "jobs": ["Software Engineer", "Data Scientist", "Network Engineer"]}

    def run_market_score(self, subject_name: str):
        if market_score_agent is not None:
            if hasattr(market_score_agent, "MarketScoreAgent"):
                try:
                    agent = market_score_agent.MarketScoreAgent()
                    ok, result = safe_call(agent.get_score, subject_name)
                    if ok:
                        return result
                except Exception:
                    pass
        # fallback heuristic
        return {"subject": subject_name, "market_score": 60.0, "meaning": "Fallback: moderate demand"}

    def run_skill_profile(self, grades_dict: dict = None, subjects_df = None):
        """
        Produce a skill profile using skill_profiler_agent or utils.ai_utils if available.
        Expects grades_dict and optionally a subjects_df path or object.
        """
        if skill_profiler_agent is not None:
            if hasattr(skill_profiler_agent, "build_skill_profile"):
                ok, profile = safe_call(skill_profiler_agent.build_skill_profile, grades_dict, subjects_df)
                if ok:
                    return {"source": "skill_profiler_agent", "profile": profile}
        # fallback empty profile
        return {"source": "fallback", "profile": {}}


class LLMOrchestrator:
    """
    Orchestrates LLM-based agents (OpenAI / Ollama callers).
    These typically produce textual or structured JSON outputs from LLMs.
    """
    def __init__(self):
        pass

    def get_career_info(self, career_name: str):
        if career_exploration is not None and hasattr(career_exploration, "get_career_info"):
            ok, result = safe_call(career_exploration.get_career_info, career_name)
            if ok:
                return {"source": "career_exploration", "career_info": result}
            else:
                return {"source": "career_exploration", "error": result}
        return {"source": "fallback", "career_info": {"title": career_name, "description": "No career info available."}}

    def get_roadmap(self, role: str, user_scores: dict = None, weeks: int = 10):
        if roadmap is not None and hasattr(roadmap, "get_roadmap"):
            ok, result = safe_call(roadmap.get_roadmap, role, user_scores or {}, weeks)
            if ok:
                return {"source": "roadmap", "roadmap": result}
            else:
                return {"source": "roadmap", "error": result}
        return {"source": "fallback", "roadmap": {}}

    def run_fact_check(self, claim: str):
        if fact_checker is not None and hasattr(fact_checker, "fact_check"):
            ok, result = safe_call(fact_checker.fact_check, claim)
            if ok:
                return {"source": "fact_checker", "fact_check": result}
            else:
                return {"source": "fact_checker", "error": result}
        return {"source": "fallback", "fact_check": {"verdict": "Uncertain", "confidence": 0.0, "explanation": "Fact-checker not available", "sources": []}}

    def run_research(self, query: str):
        if web_researcher is not None and hasattr(web_researcher, "run_research"):
            ok, result = safe_call(web_researcher.run_research, query)
            if ok:
                return {"source": "web_researcher", "research": result}
            else:
                return {"source": "web_researcher", "error": result}
        return {"source": "fallback", "research": {"topic": query, "summary": "", "sources": [], "tools_used": []}}

    def generate_linkedin_post(self, domain: str, pointers: list[str]):
        if linkedin_post_generator is not None and hasattr(linkedin_post_generator, "generate_linkedin_post"):
            ok, result = safe_call(linkedin_post_generator.generate_linkedin_post, domain, pointers)
            if ok:
                return {"source": "linkedin_post_generator", "post": result}
            else:
                return {"source": "linkedin_post_generator", "error": result}
        # fallback simple post
        text = f"{domain} — {'; '.join(pointers[:3])}"
        return {"source": "fallback", "post": text}

# ---- Master Orchestrator ----
class MasterOrchestrator:
    def __init__(self):
        self.non_llm = NonLLMOrchestrator()
        self.llm = LLMOrchestrator()

    def decide_and_call(self, message: str, user_scores: Optional[dict] = None, user: Optional[dict] = None) -> Dict[str, Any]:
        """
        Main entrypoint. Returns a dict:
        {
            "type": "career"/"roadmap"/"job_recommendation"/"market"/"research"/"linkedin"/"unknown",
            "intent": <from classifier>,
            "payload": <text reply>,
            "structured": <structured data produced by non-LLM agents or LLM json>,
            "meta": {...}
        }
        """
        try:
            m = (message or "").strip()
            if not m:
                return {"type": "unknown", "intent": "none", "payload": "Please provide a prompt.", "structured": None, "meta": {}}

            # 1) classify intent (rule-based)
            classifier_result = self.non_llm.intent_from_prompt(m)
            intent = classifier_result.get("intent", "other")

            # Use keywords to detect explicit user intentions
            lower = m.lower()

            # Priority: explicit career/roadmap queries (LLM), job recommend (non-LLM), market/profile requests (non-LLM), research/fact-check/linkedin (LLM)
            # Career info (LLM)
            if "tell me about" in lower or lower.startswith("career") or "what is a" in lower or "what does a" in lower:
                # parse target
                if "about" in lower:
                    parts = message.split("about", 1)
                    target = parts[1].strip()
                else:
                    target = message
                llm_res = self.llm.get_career_info(target)
                payload = dict_to_string(llm_res.get("career_info") or llm_res.get("error") or "")
                return {"type": "career", "intent": intent, "payload": payload, "structured": llm_res, "meta": {"source": llm_res.get("source")}}

            # Roadmap
            if "how to become" in lower or "roadmap" in lower or lower.startswith("how to"):
                # find role
                for phrase in ["how to become", "roadmap to become", "roadmap for", "how to"]:
                    if phrase in lower:
                        role = message.lower().split(phrase,1)[1].strip()
                        break
                else:
                    role = message
                llm_res = self.llm.get_roadmap(role, user_scores or {}, weeks=10)
                payload = dict_to_string(llm_res.get("roadmap") or llm_res.get("error") or "")
                return {"type": "roadmap", "intent": intent, "payload": payload, "structured": llm_res, "meta": {"source": llm_res.get("source")}}

            # Job recommendation (non-LLM)
            if "recommend" in lower or "suggest job" in lower or "which job" in lower or "job for me" in lower or intent == "recommendation":
                nonllm_res = self.non_llm.run_job_recommendation(user_scores or {})
                # job lists sometimes are returned as list or dataframe; stringify appropriately
                jobs = nonllm_res.get("jobs")
                payload = dict_to_string(jobs)
                return {"type": "job_recommendation", "intent": intent, "payload": payload, "structured": nonllm_res, "meta": {}}

            # Market score for a subject
            if "market" in lower or "demand" in lower or intent == "market":
                # attempt to extract subject after 'market' or 'demand for'
                subject = None
                if "for" in lower:
                    # naive extraction: take words after 'for'
                    parts = lower.split("for",1)[1].strip()
                    subject = parts
                else:
                    subject = message
                nonllm_res = self.non_llm.run_market_score(subject)
                payload = dict_to_string(nonllm_res)
                return {"type": "market", "intent": intent, "payload": payload, "structured": nonllm_res, "meta": {}}

            # Skill profile / charts
            if "profile" in lower or "skills" in lower or intent == "profile":
                # try skill_profiler_agent to get profile
                nonllm_res = self.non_llm.run_skill_profile(user_scores or {}, None)
                payload = dict_to_string(nonllm_res.get("profile"))
                return {"type": "profile", "intent": intent, "payload": payload, "structured": nonllm_res, "meta": {}}

            # Research
            if "research" in lower or "find" in lower or "who is" in lower or "what is" in lower and ("research" in lower or "summar" in lower):
                llm_res = self.llm.run_research(message)
                payload = dict_to_string(llm_res.get("research") or llm_res.get("error") or "")
                return {"type": "research", "intent": intent, "payload": payload, "structured": llm_res, "meta": {"source": llm_res.get("source")}}

            # LinkedIn post generation (LLM): user asks "write linkedin post" or "create post"
            if "linkedin" in lower or "post" in lower and ("linkedin" in lower or "write" in lower or "create" in lower):
                # naive: if user included domain and pointers separated by ':' or newline, try parse
                # otherwise try to use last job_recommendation results as pointers
                # Expect user to provide: "linkedin: domain=AI; points=Built X; Learned Y"
                domain = None
                pointers = []
                # simple parse: if message contains 'domain:' or 'pointers:' parse them
                if "domain:" in lower:
                    try:
                        parts = message.split("domain:",1)[1]
                        domain = parts.split()[0].strip()
                    except Exception:
                        domain = "General"
                # pointers: split sentences after 'points:' or after newline
                if "points:" in lower:
                    try:
                        pts = message.split("points:",1)[1]
                        pointers = [p.strip() for p in pts.split(";") if p.strip()]
                    except Exception:
                        pointers = []
                # fallback pointers and domain
                if not domain:
                    domain = "General"
                if not pointers:
                    pointers = [message[:200]]
                llm_res = self.llm.generate_linkedin_post(domain, pointers)
                payload = dict_to_string(llm_res.get("post") or llm_res.get("error") or "")
                return {"type": "linkedin", "intent": intent, "payload": payload, "structured": llm_res, "meta": {"source": llm_res.get("source")}}

            # Fact check
            if "check" in lower and ("fact" in lower or "true" in lower or "verify" in lower):
                # extract claim naive
                claim = message
                llm_res = self.llm.run_fact_check(claim)
                payload = dict_to_string(llm_res.get("fact_check") or llm_res.get("error") or "")
                return {"type": "fact_check", "intent": intent, "payload": payload, "structured": llm_res, "meta": {}}

            # Fallback: if nothing matched, try LLM research and fallback to job rec
            # Try career info for single-word prompts (e.g., "Data Scientist")
            if len(message.split()) <= 3:
                # assume career
                llm_res = self.llm.get_career_info(message)
                payload = dict_to_string(llm_res.get("career_info") or llm_res.get("error") or "")
                return {"type": "career_guess", "intent": intent, "payload": payload, "structured": llm_res, "meta": {"note": "assumed short prompt means career query"}}

            # final fallback
            return {"type": "unknown", "intent": intent, "payload": "Sorry, I couldn't understand. Try 'Tell me about Data Scientist', 'How to become Data Scientist', or 'Recommend jobs for me'.", "structured": None, "meta": {}}
        except Exception as e:
            tb = traceback.format_exc()
            return {"type": "error", "intent": "error", "payload": f"Orchestrator error: {e}", "structured": {"traceback": tb}, "meta": {}}


# Provide an easy-to-import function for app.py
_master = MasterOrchestrator()

def decide_and_call(message: str, user_scores: Optional[dict] = None, user: Optional[dict] = None):
    return _master.decide_and_call(message, user_scores=user_scores, user=user)





















# # orchestrator.py
# from agents import career_exploration, roadmap, job_recommendation

# def dict_to_string(d):
#     """Convert dict to readable string for chat"""
#     if not isinstance(d, dict):
#         return str(d)
#     text = ""
#     for k, v in d.items():
#         if isinstance(v, list):
#             v = ", ".join(map(str, v))
#         text += f"{k.capitalize()}: {v}\n"
#     return text

# def decide_and_call(message: str, user_scores=None):
#     m = message.lower().strip()

#     # Career exploration
#     if "tell me about" in m or m.startswith("career"):
#         parts = message.split("about", 1)
#         target = parts[1].strip() if len(parts) > 1 else message
#         info = career_exploration.get_career_info(target)
#         payload = dict_to_string(info)
#         return {"type": "career", "payload": payload}

#     # Roadmap
#     if "how to become" in m or "roadmap" in m or "plan to become" in m or m.startswith("how to"):
#         for phrase in ["how to become", "roadmap to become", "roadmap for", "how to"]:
#             if phrase in m:
#                 role = m.split(phrase,1)[1].strip()
#                 break
#         else:
#             role = message
#         info = roadmap.get_roadmap(role, user_scores or {}, weeks=10)
#         payload = dict_to_string(info) if isinstance(info, dict) else str(info)
#         return {"type": "roadmap", "payload": payload}

#     # Job recommendation
#     if "recommend" in m or "suggest job" in m or "which job" in m or "job for me" in m:
#         vals = None
#         if isinstance(user_scores, dict):
#             order = ['DSA','DBMS','OS','CN','Mathmetics','Aptitute','Comm','Problem_Solving','Creative','Hackathons']
#             vals = [user_scores.get(k,0) for k in order]
#         else:
#             vals = [50]*10
#         payload = job_recommendation.predict_jobs_from_list(vals)
#         payload = dict_to_string(payload) if isinstance(payload, dict) else str(payload)
#         return {"type": "job_recommendation", "payload": payload}

#     # fallback
#     return {"type": "unknown", "payload": "Sorry, I couldn't understand. Try asking 'Tell me about Data Scientist' or 'How to become Data Scientist' or 'Give me job recommendation'."}
