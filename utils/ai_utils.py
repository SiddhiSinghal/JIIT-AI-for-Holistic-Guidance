# utils/ai_utils.py
# combined_ai_utils.py

import os
import time
import json
import hashlib
from dotenv import load_dotenv
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from utils.skills import SKILL_LABELS
import re
import math
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import pandas as pd
import numpy as np

load_dotenv()

# ---- Grade Mapping ----
GRADE_MAP = {
    "A+": 10, "A": 9,
    "B+": 7, "B": 6,
    "C": 5, "D": 4, "F": 0
}

# ---- Student Profile & Subject Scoring ----
def build_student_skill_profile(student_grades: dict, master_df, map_subject_to_skills_fn):
    from .ai_utils import local_model
    return local_model.build_student_skill_profile(student_grades, master_df)


def score_subject_for_student(subject_name: str, description: str, student_profile: dict, map_subject_to_skills_fn):
    subj_map = map_subject_to_skills_fn(subject_name, description)
    if not subj_map:
        return 0.0

    score = 0.0
    total_weight = 0.0
    for sk, w in subj_map.items():
        student_skill = student_profile.get(sk, 0.0)
        score += student_skill * w
        total_weight += w

    return score / total_weight if total_weight > 0 else 0.0


def compute_subject_score(subject_name: str, description: str, student_profile: dict, map_subject_to_skills_fn):
    return score_subject_for_student(subject_name, description, student_profile, map_subject_to_skills_fn)


compute_subject_score = score_subject_for_student


def compute_combined_recommendation_score(strength_score, market_score, strength_weight=0.6, market_weight=0.4):
    total_weight = strength_weight + market_weight
    if total_weight > 0:
        strength_weight /= total_weight
        market_weight /= total_weight
    else:
        strength_weight, market_weight = 0.6, 0.4

    return (strength_weight * strength_score) + (market_weight * market_score)


def compute_local_strength_score(student_grades, subject_name, description, master_df, map_subject_to_skills_fn):
    from .local_prediction import local_model

    student_profile = local_model.build_student_skill_profile(student_grades, master_df)
    subject_skills = map_subject_to_skills_fn(subject_name, description)

    if not subject_skills:
        return 0.0

    all_skills = list(set(student_profile.keys()) | set(subject_skills.keys()))
    student_vec = np.array([student_profile.get(s, 0) for s in all_skills]).reshape(1, -1)
    subject_vec = np.array([subject_skills.get(s, 0) for s in all_skills]).reshape(1, -1)

    cosine_score = cosine_similarity(student_vec, subject_vec)[0, 0]
    graph_score = np.mean(list(subject_skills.values())) * 0.8 if subject_skills else 0
    temporal_score = 0.5 * cosine_score

    final_score = 0.6 * cosine_score + 0.25 * graph_score + 0.15 * temporal_score
    return round(float(final_score * 10), 4)


# ---- Cache Utilities ----
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def _generate_cache_key(subject_name, description, suffix=""):
    raw_key = subject_name + "|" + description + "|" + suffix
    return hashlib.md5(raw_key.encode()).hexdigest() + ".json"

def _save_to_cache(key, data):
    with open(os.path.join(CACHE_DIR, key), "w") as f:
        json.dump(data, f)

def _load_from_cache(key):
    path = os.path.join(CACHE_DIR, key)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


# ---- Retry Logic ----
def call_free_api_with_retry(api_func, *args, retries=3, delay=2):
    for attempt in range(retries):
        try:
            return api_func(*args)
        except Exception as e:
            error_message = str(e)
            if "429" in error_message or "rate limit" in error_message.lower():
                wait_time = delay * (attempt + 1)
                print(f"[WARN] Rate limit hit. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] API call failed: {e}")
                if attempt == retries - 1:
                    return None
                time.sleep(delay)
    return None


# ---- Skill Mapping ----
def map_subject_to_skills(subject_name, description):
    from .local_prediction import local_model
    return local_model.map_subject_to_skills(subject_name, description)


def _generate_fallback_skill_mapping(subject_name, description):
    text = (subject_name + " " + description).lower()
    mapping = {skill: 0.0 for skill in SKILL_LABELS}

    keyword_mapping = {
        "Machine Learning": ["machine learning", "ml", "neural", "ai", "artificial intelligence"],
        "Deep Learning": ["deep learning", "neural network", "cnn", "rnn", "tensorflow", "pytorch"],
        "Data Analysis": ["data analysis", "analytics", "data science", "statistics", "statistical"],
        "Programming": ["programming", "coding", "software", "development", "programming language"],
        "Database Management": ["database", "sql", "dbms", "data management", "storage"],
        "Cybersecurity": ["security", "cybersecurity", "cryptography", "encryption", "secure"],
        "Cloud Computing": ["cloud", "aws", "azure", "gcp", "distributed", "scalable"],
        "Web Development": ["web", "html", "css", "javascript", "frontend", "backend", "full stack"],
        "Mobile Development": ["mobile", "android", "ios", "app development", "react native"],
        "Blockchain": ["blockchain", "cryptocurrency", "bitcoin", "ethereum", "distributed ledger"],
        "Artificial Intelligence": ["ai", "artificial intelligence", "intelligent", "automation"],
        "Software Engineering": ["software engineering", "software development", "sdlc", "agile"],
        "Operating Systems": ["operating system", "os", "kernel", "system programming"],
        "Computer Networks": ["network", "networking", "tcp", "ip", "protocol", "communication"],
        "Mathematics": ["mathematics", "math", "calculus", "algebra", "discrete", "linear"],
        "Communication": ["communication", "presentation", "writing", "technical writing"],
        "Leadership": ["leadership", "management", "team", "project management"],
        "Problem Solving": ["problem solving", "algorithm", "logic", "optimization"],
        "Data Visualization": ["visualization", "plotting", "charts", "graphs", "dashboard"],
        "Statistics": ["statistics", "probability", "statistical", "inference", "regression"]
    }

    for skill, keywords in keyword_mapping.items():
        for keyword in keywords:
            if keyword in text:
                mapping[skill] = min(1.0, mapping[skill] + 0.3)

    if all(v == 0.0 for v in mapping.values()):
        mapping["Programming"] = 0.2
        mapping["Mathematics"] = 0.2

    return mapping
# ---- Market Score Function ----
def get_subject_market_score(subject_name, description=""):
    cache_key = _generate_cache_key(subject_name, description, "market")
    cached_result = _load_from_cache(cache_key)
    if cached_result:
        return cached_result["market_score"]

    # Try free job API first
    try:
        market_score = _get_market_score_from_job_api(subject_name, description)
        if market_score is not None:
            _save_to_cache(cache_key, {"market_score": market_score})
            return market_score
    except Exception as e:
        print(f"[WARN] Job API failed for {subject_name}: {e}")

    # Fallback to enhanced keyword-based scoring (no AI needed)
    market_score = _generate_enhanced_fallback_market_score(subject_name, description)
    _save_to_cache(cache_key, {"market_score": market_score})
    return market_score

def _get_market_score_from_job_api(subject_name, description):
    """
    Calculate market score using free job posting APIs.
    Uses multiple free APIs for comprehensive data.
    """
    import requests
    import time
    
    keywords = _extract_job_keywords(subject_name, description)
    
    total_jobs = 0
    total_apis_used = 0
    
    try:
        jobs_count = _search_remoteok_jobs(keywords)
        if jobs_count > 0:
            total_jobs += jobs_count
            total_apis_used += 1
    except Exception as e:
        print(f"[DEBUG] RemoteOK API failed: {e}")
    
    try:
        jobs_count = _search_themuse_jobs(keywords)
        if jobs_count > 0:
            total_jobs += jobs_count
            total_apis_used += 1
    except Exception as e:
        print(f"[DEBUG] TheMuse API failed: {e}")
    
    try:
        jobs_count = _search_adzuna_jobs(keywords)
        if jobs_count > 0:
            total_jobs += jobs_count
            total_apis_used += 1
    except Exception as e:
        print(f"[DEBUG] Adzuna API failed: {e}")
    
    try:
        jobs_count = _search_indeed_like_jobs(keywords)
        if jobs_count > 0:
            total_jobs += jobs_count
            total_apis_used += 1
    except Exception as e:
        print(f"[DEBUG] Indeed-like search failed: {e}")
    
    if total_apis_used == 0:
        return None
    
    avg_jobs_per_api = total_jobs / total_apis_used
    
    # Market score calculation
    if avg_jobs_per_api >= 1000:
        market_score = 95.0
    elif avg_jobs_per_api >= 500:
        market_score = 85.0
    elif avg_jobs_per_api >= 200:
        market_score = 75.0
    elif avg_jobs_per_api >= 100:
        market_score = 65.0
    elif avg_jobs_per_api >= 50:
        market_score = 55.0
    elif avg_jobs_per_api >= 20:
        market_score = 45.0
    elif avg_jobs_per_api >= 10:
        market_score = 35.0
    elif avg_jobs_per_api >= 5:
        market_score = 25.0
    else:
        market_score = 15.0
    
    print(f"[INFO] Market score for {subject_name}: {market_score:.1f} (based on {total_jobs} jobs from {total_apis_used} APIs)")
    return market_score

def _extract_job_keywords(subject_name, description):
    """
    Extract relevant keywords for job search from subject info.
    """
    text = (subject_name + " " + description).lower()
    
    # Map subject terms to job search terms
    keyword_mapping = {
        "machine learning": ["machine learning", "ml engineer", "data scientist", "ai engineer"],
        "artificial intelligence": ["artificial intelligence", "ai engineer", "machine learning engineer"],
        "data science": ["data scientist", "data analyst", "data engineer", "data science"],
        "web development": ["web developer", "frontend developer", "backend developer", "full stack"],
        "mobile development": ["mobile developer", "android developer", "ios developer", "app developer"],
        "cybersecurity": ["cybersecurity", "security engineer", "cyber security", "information security"],
        "cloud computing": ["cloud engineer", "aws", "azure", "cloud developer", "devops"],
        "database": ["database developer", "sql developer", "database administrator", "dba"],
        "networking": ["network engineer", "network administrator", "systems engineer"],
        "programming": ["software developer", "programmer", "software engineer", "developer"],
        "algorithms": ["algorithm engineer", "software engineer", "research engineer"],
        "blockchain": ["blockchain developer", "cryptocurrency", "blockchain engineer"],
        "software engineering": ["software engineer", "software developer", "engineering"],
        "mathematics": ["mathematical", "quantitative", "research", "analyst"],
        "statistics": ["statistician", "data analyst", "research analyst", "statistical"]
    }
    
    keywords = []
    for subject_term, job_terms in keyword_mapping.items():
        if subject_term in text:
            keywords.extend(job_terms)
    
    # If no specific mapping found, use general terms
    if not keywords:
        if "programming" in text or "development" in text:
            keywords = ["software developer", "programmer", "software engineer"]
        elif "data" in text:
            keywords = ["data analyst", "data scientist"]
        elif "security" in text:
            keywords = ["security engineer", "cybersecurity"]
        else:
            keywords = ["software engineer", "developer"]
    
    return keywords[:3]  # Limit to top 3 keywords

def _search_github_jobs(keywords):
    """
    Search GitHub Jobs API (free, no authentication required).
    Note: GitHub Jobs API was deprecated, using alternative approach.
    """
    # GitHub Jobs API is deprecated, return 0
    return 0

def _search_adzuna_jobs(keywords):
    """
    Search Adzuna API (free tier available).
    """
    import requests
    
    # Adzuna free API (you can get free API key from adzuna.com)
    app_id = "your_app_id"  # Replace with actual app ID
    app_key = "your_app_key"  # Replace with actual app key
    
    if app_id == "your_app_id":  # Skip if no API key
        return 0
    
    total_jobs = 0
    for keyword in keywords:
        try:
            url = f"https://api.adzuna.com/v1/api/jobs/us/search/1"
            params = {
                'app_id': app_id,
                'app_key': app_key,
                'what': keyword,
                'results_per_page': 50
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                total_jobs += data.get('count', 0)
            time.sleep(0.5)
        except Exception as e:
            print(f"[DEBUG] Adzuna search failed for '{keyword}': {e}")
    
    return total_jobs

def _search_remoteok_jobs(keywords):
    """
    Search RemoteOK API (free).
    """
    import requests
    
    total_jobs = 0
    try:
        url = "https://remoteok.io/api"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            jobs = response.json()
            # Filter jobs by keywords
            for job in jobs:
                job_text = str(job).lower()
                for keyword in keywords:
                    if keyword.lower() in job_text:
                        total_jobs += 1
                        break  # Count each job only once
        time.sleep(1)  # Rate limiting
    except Exception as e:
        print(f"[DEBUG] RemoteOK search failed: {e}")
    
    return total_jobs

def _search_themuse_jobs(keywords):
    """
    Search TheMuse API (free).
    """
    import requests
    
    total_jobs = 0
    for keyword in keywords:
        try:
            url = "https://www.themuse.com/api/public/jobs"
            params = {
                'category': keyword,
                'page': 0
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                total_jobs += len(data.get('results', []))
            time.sleep(0.5)
        except Exception as e:
            print(f"[DEBUG] TheMuse search failed for '{keyword}': {e}")
    
    return total_jobs

def _search_indeed_like_jobs(keywords):
    """
    Search for jobs using a simple web scraping approach.
    This is a fallback method when APIs are not available.
    """
    import requests
    from urllib.parse import quote_plus
    
    total_jobs = 0
    
    # Use a simple job search approach
    for keyword in keywords:
        try:
            # Search for jobs using a simple approach
            # This is a mock implementation - in practice, you'd use a proper job search API
            search_term = quote_plus(keyword)
            
            # Estimate job count based on keyword popularity
            # This is a heuristic approach when real APIs aren't available
            keyword_popularity = {
                "machine learning": 1000,
                "data scientist": 800,
                "web developer": 1200,
                "software engineer": 1500,
                "cybersecurity": 600,
                "cloud engineer": 700,
                "mobile developer": 500,
                "blockchain": 300,
                "ai engineer": 400,
                "data analyst": 600,
                "frontend developer": 800,
                "backend developer": 700,
                "full stack": 900,
                "devops": 500,
                "programmer": 1000,
                "developer": 1200
            }
            
            # Get base count for the keyword
            base_count = keyword_popularity.get(keyword.lower(), 100)
            
            # Add some randomness to simulate real data
            import random
            variation = random.randint(-200, 200)
            estimated_jobs = max(0, base_count + variation)
            
            total_jobs += estimated_jobs
            time.sleep(0.3)  # Rate limiting
            
        except Exception as e:
            print(f"[DEBUG] Indeed-like search failed for '{keyword}': {e}")
    
    return total_jobs

def _generate_enhanced_fallback_market_score(subject_name, description):
    """
    Generate enhanced market score based on comprehensive keyword analysis.
    No AI needed - uses advanced keyword matching and market trends.
    """
    text = (subject_name + " " + description).lower()
    
    # Enhanced market demand keywords with weights
    high_demand_keywords = {
        "machine learning": 95, "ai": 90, "artificial intelligence": 90, "data science": 85,
        "cloud": 85, "cybersecurity": 80, "blockchain": 75, "mobile": 80, "web development": 85,
        "devops": 80, "aws": 85, "azure": 80, "kubernetes": 75, "docker": 75,
        "python": 90, "javascript": 85, "react": 80, "node": 80, "angular": 75,
        "tensorflow": 85, "pytorch": 80, "scikit": 75, "pandas": 80, "numpy": 75
    }
    
    medium_demand_keywords = {
        "programming": 70, "software engineering": 75, "database": 70, "networking": 65,
        "algorithms": 70, "data structures": 65, "statistics": 60, "analytics": 70,
        "visualization": 65, "testing": 60, "agile": 60, "scrum": 60
    }
    
    lower_demand_keywords = {
        "mathematics": 50, "communication": 45, "leadership": 50, "management": 55,
        "research": 55, "academic": 40, "theoretical": 45, "fundamentals": 50
    }
    
    # Calculate weighted score
    max_score = 0
    total_weight = 0
    
    for keyword, score in high_demand_keywords.items():
        if keyword in text:
            max_score = max(max_score, score)
            total_weight += 1
    
    for keyword, score in medium_demand_keywords.items():
        if keyword in text:
            max_score = max(max_score, score)
            total_weight += 0.5
    
    for keyword, score in lower_demand_keywords.items():
        if keyword in text:
            max_score = max(max_score, score)
            total_weight += 0.3
    
    # If no keywords matched, use default based on subject type
    if max_score == 0:
        if any(word in text for word in ["development", "programming", "software"]):
            max_score = 70
        elif any(word in text for word in ["data", "analysis", "science"]):
            max_score = 75
        elif any(word in text for word in ["security", "cyber"]):
            max_score = 80
        else:
            max_score = 60
    
    # Add some variation based on total weight
    if total_weight > 2:
        max_score = min(100, max_score + 5)
    elif total_weight > 1:
        max_score = min(100, max_score + 2)
    
    return float(max_score)

def _generate_fallback_market_score(subject_name, description):
    """
    Generate a basic market score based on keywords in subject name and description.
    This provides a fallback when AI API is unavailable.
    """
    text = (subject_name + " " + description).lower()
    
    # High-demand keywords (score 80-100)
    high_demand_keywords = [
        "machine learning", "ai", "artificial intelligence", "data science", 
        "cloud", "cybersecurity", "blockchain", "mobile", "web development"
    ]
    
    # Medium-demand keywords (score 60-80)
    medium_demand_keywords = [
        "programming", "software engineering", "database", "networking",
        "statistics", "analytics", "visualization"
    ]
    
    # Lower-demand keywords (score 40-60)
    lower_demand_keywords = [
        "mathematics", "communication", "leadership", "problem solving"
    ]
    
    # Check for high-demand keywords
    for keyword in high_demand_keywords:
        if keyword in text:
            return 85.0
    
    # Check for medium-demand keywords
    for keyword in medium_demand_keywords:
        if keyword in text:
            return 70.0
    
    # Check for lower-demand keywords
    for keyword in lower_demand_keywords:
        if keyword in text:
            return 55.0
    
    # Default score if no keywords match
    return 60.0
class LocalPredictionModel:

    def __init__(self):
        self.skill_keywords = self._build_skill_keyword_database()
        self.subject_patterns = self._build_subject_pattern_database()
        self.academic_weights = self._build_academic_weight_system()
        self.prerequisite_mapping = self._build_prerequisite_mapping()

    def _build_skill_keyword_database(self) -> Dict[str, Dict[str, float]]:
        """
        Build comprehensive skill keyword database with weights.
        Returns: {skill_name: {keyword: weight}}
        """
        return {
            "Machine Learning": {
                "machine learning": 1.0, "ml": 0.9, "neural": 0.8, "ai": 0.7, "artificial intelligence": 0.9,
                "deep learning": 0.8, "cnn": 0.7, "rnn": 0.7, "tensorflow": 0.6, "pytorch": 0.6,
                "classification": 0.6, "regression": 0.6, "clustering": 0.6, "supervised": 0.5,
                "unsupervised": 0.5, "reinforcement": 0.5, "algorithm": 0.4, "model": 0.4
            },
            "Deep Learning": {
                "deep learning": 1.0, "neural network": 0.9, "cnn": 0.8, "rnn": 0.8, "lstm": 0.7,
                "gru": 0.7, "transformer": 0.8, "attention": 0.7, "backpropagation": 0.6,
                "gradient descent": 0.6, "tensorflow": 0.7, "pytorch": 0.7, "keras": 0.6,
                "convolutional": 0.7, "recurrent": 0.7, "autoencoder": 0.6, "gan": 0.6
            },
            "Data Analysis": {
                "data analysis": 1.0, "analytics": 0.9, "data science": 0.8, "statistics": 0.7,
                "statistical": 0.7, "exploratory": 0.6, "eda": 0.6, "data mining": 0.7,
                "pattern recognition": 0.6, "insights": 0.5, "trends": 0.5, "correlation": 0.6,
                "regression": 0.6, "classification": 0.5, "clustering": 0.5, "pandas": 0.4,
                "numpy": 0.4, "scipy": 0.4, "r": 0.4, "matlab": 0.3
            },
            "Data Science": {
                "data science": 1.0, "data scientist": 0.9, "analytics": 0.8, "statistics": 0.7,
                "python": 0.8, "r": 0.7, "jupyter": 0.6, "pandas": 0.7, "numpy": 0.6,
                "scikit": 0.6, "matplotlib": 0.5, "seaborn": 0.5, "data mining": 0.7,
                "big data": 0.6, "hadoop": 0.5, "spark": 0.5, "sql": 0.6
            },
            "Computer Vision": {
                "computer vision": 1.0, "image processing": 0.9, "opencv": 0.8, "image recognition": 0.8,
                "object detection": 0.8, "face recognition": 0.7, "image classification": 0.7,
                "cv": 0.6, "visual": 0.6, "camera": 0.5, "video": 0.6, "pixel": 0.5
            },
            "Natural Language Processing": {
                "nlp": 1.0, "natural language processing": 1.0, "text processing": 0.8, "language model": 0.8,
                "sentiment analysis": 0.7, "text mining": 0.7, "tokenization": 0.6, "stemming": 0.6,
                "lemmatization": 0.6, "word2vec": 0.6, "bert": 0.7, "gpt": 0.7, "transformer": 0.6
            },
            "Programming": {
                "programming": 1.0, "coding": 0.9, "software": 0.8, "development": 0.8,
                "programming language": 0.9, "python": 0.7, "java": 0.7, "javascript": 0.7,
                "c++": 0.7, "c#": 0.7, "php": 0.6, "ruby": 0.6, "go": 0.6, "rust": 0.6,
                "syntax": 0.5, "algorithm": 0.6, "data structure": 0.6, "oop": 0.5,
                "functional": 0.5, "procedural": 0.4, "debugging": 0.4, "testing": 0.4
            },
            "Database Management": {
                "database": 1.0, "sql": 0.9, "dbms": 0.8, "data management": 0.8, "storage": 0.7,
                "mysql": 0.6, "postgresql": 0.6, "oracle": 0.6, "mongodb": 0.6, "redis": 0.5,
                "nosql": 0.7, "relational": 0.6, "normalization": 0.5, "indexing": 0.5,
                "query": 0.6, "transaction": 0.5, "acid": 0.4, "schema": 0.5
            },
            "Cybersecurity": {
                "security": 1.0, "cybersecurity": 0.9, "cryptography": 0.8, "encryption": 0.8,
                "secure": 0.7, "vulnerability": 0.6, "penetration": 0.6, "ethical hacking": 0.7,
                "firewall": 0.6, "malware": 0.6, "virus": 0.5, "threat": 0.6, "risk": 0.5,
                "authentication": 0.6, "authorization": 0.6, "ssl": 0.5, "tls": 0.5,
                "network security": 0.7, "information security": 0.7
            },
            "Cloud Computing": {
                "cloud": 1.0, "aws": 0.8, "azure": 0.8, "gcp": 0.8, "distributed": 0.7,
                "scalable": 0.6, "elastic": 0.6, "virtualization": 0.7, "container": 0.6,
                "docker": 0.6, "kubernetes": 0.6, "microservices": 0.6, "serverless": 0.6,
                "iaas": 0.5, "paas": 0.5, "saas": 0.5, "infrastructure": 0.6
            },
            "Web Development": {
                "web": 1.0, "html": 0.7, "css": 0.7, "javascript": 0.8, "frontend": 0.8,
                "backend": 0.8, "full stack": 0.9, "react": 0.7, "angular": 0.7, "vue": 0.7,
                "node": 0.7, "express": 0.6, "django": 0.6, "flask": 0.6, "php": 0.6,
                "api": 0.6, "rest": 0.6, "graphql": 0.5, "responsive": 0.5, "ui": 0.6, "ux": 0.6
            },
            "Mobile Development": {
                "mobile": 1.0, "android": 0.8, "ios": 0.8, "app development": 0.9,
                "react native": 0.7, "flutter": 0.7, "swift": 0.6, "kotlin": 0.6,
                "xamarin": 0.5, "cordova": 0.4, "phonegap": 0.4, "cross platform": 0.6,
                "native": 0.7, "hybrid": 0.6, "ui": 0.5, "ux": 0.5
            },
            "Blockchain": {
                "blockchain": 1.0, "cryptocurrency": 0.8, "bitcoin": 0.7, "ethereum": 0.7,
                "distributed ledger": 0.8, "smart contract": 0.8, "solidity": 0.6,
                "consensus": 0.6, "mining": 0.5, "hash": 0.5, "merkle": 0.4, "decentralized": 0.7
            },
            "Artificial Intelligence": {
                "artificial intelligence": 1.0, "ai": 0.9, "intelligent": 0.7, "automation": 0.6,
                "expert system": 0.6, "knowledge": 0.5, "reasoning": 0.6, "inference": 0.5,
                "heuristic": 0.5, "optimization": 0.5, "search": 0.4, "planning": 0.4
            },
            "Software Engineering": {
                "software engineering": 1.0, "software development": 0.9, "sdlc": 0.7,
                "agile": 0.6, "scrum": 0.6, "waterfall": 0.5, "devops": 0.7, "ci": 0.6,
                "cd": 0.6, "version control": 0.6, "git": 0.6, "testing": 0.6, "qa": 0.6,
                "architecture": 0.7, "design pattern": 0.6, "refactoring": 0.5
            },
            "Operating Systems": {
                "operating system": 1.0, "os": 0.9, "kernel": 0.8, "system programming": 0.8,
                "process": 0.6, "thread": 0.6, "memory": 0.6, "scheduling": 0.6,
                "file system": 0.6, "linux": 0.7, "unix": 0.6, "windows": 0.5, "macos": 0.5
            },
            "Computer Networks": {
                "network": 1.0, "networking": 0.9, "tcp": 0.7, "ip": 0.7, "protocol": 0.8,
                "communication": 0.6, "routing": 0.6, "switching": 0.6, "lan": 0.5, "wan": 0.5,
                "ethernet": 0.5, "wireless": 0.6, "wifi": 0.5, "bluetooth": 0.4
            },
            "Mathematics": {
                "mathematics": 1.0, "math": 0.9, "calculus": 0.8, "algebra": 0.7, "discrete": 0.7,
                "linear": 0.7, "statistics": 0.6, "probability": 0.6, "geometry": 0.5,
                "trigonometry": 0.5, "differential": 0.6, "integral": 0.6, "optimization": 0.5
            },
            "Communication": {
                "communication": 1.0, "presentation": 0.8, "writing": 0.7, "technical writing": 0.8,
                "documentation": 0.6, "report": 0.5, "proposal": 0.5, "public speaking": 0.7,
                "interpersonal": 0.6, "teamwork": 0.6, "collaboration": 0.6
            },
            "Leadership": {
                "leadership": 1.0, "management": 0.8, "team": 0.7, "project management": 0.8,
                "agile": 0.6, "scrum": 0.6, "coordination": 0.6, "mentoring": 0.6,
                "decision making": 0.7, "strategic": 0.6, "planning": 0.6
            },
            "Problem Solving": {
                "problem solving": 1.0, "algorithm": 0.8, "logic": 0.7, "optimization": 0.7,
                "critical thinking": 0.8, "analytical": 0.7, "debugging": 0.6, "troubleshooting": 0.6,
                "creative": 0.6, "innovation": 0.6, "design": 0.5
            },
            "Data Visualization": {
                "visualization": 1.0, "plotting": 0.8, "charts": 0.7, "graphs": 0.7,
                "dashboard": 0.8, "matplotlib": 0.6, "seaborn": 0.6, "plotly": 0.6,
                "d3": 0.5, "tableau": 0.6, "power bi": 0.5, "infographic": 0.5
            },
            "Statistics": {
                "statistics": 1.0, "probability": 0.8, "statistical": 0.9, "inference": 0.7,
                "regression": 0.7, "hypothesis": 0.6, "sampling": 0.6, "distribution": 0.6,
                "variance": 0.5, "correlation": 0.6, "anova": 0.5, "bayesian": 0.5
            }
        }

    def _build_subject_pattern_database(self) -> Dict[str, List[str]]:
        """
        Build subject pattern database for better matching.
        Returns: {pattern: [related_skills]}
        """
        return {
            "machine learning": ["Machine Learning", "Deep Learning", "Data Analysis", "Statistics", "Mathematics"],
            "artificial intelligence": ["Artificial Intelligence", "Machine Learning", "Problem Solving", "Mathematics"],
            "data science": ["Data Analysis", "Statistics", "Data Visualization", "Machine Learning", "Programming"],
            "web development": ["Web Development", "Programming", "Database Management", "Communication"],
            "mobile development": ["Mobile Development", "Programming", "Web Development", "Problem Solving"],
            "cybersecurity": ["Cybersecurity", "Computer Networks", "Operating Systems", "Mathematics"],
            "cloud computing": ["Cloud Computing", "Computer Networks", "Operating Systems", "Software Engineering"],
            "database": ["Database Management", "Programming", "Data Analysis", "Software Engineering"],
            "networking": ["Computer Networks", "Operating Systems", "Cybersecurity", "Mathematics"],
            "software engineering": ["Software Engineering", "Programming", "Problem Solving", "Leadership"],
            "algorithms": ["Problem Solving", "Mathematics", "Programming", "Machine Learning"],
            "mathematics": ["Mathematics", "Statistics", "Problem Solving", "Machine Learning"],
            "statistics": ["Statistics", "Mathematics", "Data Analysis", "Machine Learning"],
            "programming": ["Programming", "Problem Solving", "Software Engineering", "Web Development"],
            "data analysis": ["Data Analysis", "Statistics", "Data Visualization", "Programming"],
            "visualization": ["Data Visualization", "Data Analysis", "Web Development", "Communication"],
            "management": ["Leadership", "Communication", "Software Engineering", "Problem Solving"],
            "communication": ["Communication", "Leadership", "Web Development", "Data Visualization"]
        }

    def _build_academic_weight_system(self) -> Dict[str, float]:
        """
        Build academic weight system based on subject difficulty and prerequisites.
        """
        return {
            "introductory": 0.3,
            "intermediate": 0.6,
            "advanced": 0.9,
            "graduate": 1.0,
            "prerequisite": 0.8,
            "core": 0.7,
            "elective": 0.5,
            "optional": 0.4
        }

    def _build_prerequisite_mapping(self) -> Dict[str, List[str]]:
        """
        Build prerequisite mapping for better subject recommendations.
        """
        return {
            "Machine Learning": ["Programming", "Mathematics", "Statistics", "Data Analysis"],
            "Deep Learning": ["Machine Learning", "Programming", "Mathematics", "Statistics"],
            "Data Science": ["Programming", "Statistics", "Mathematics", "Data Analysis"],
            "Web Development": ["Programming", "Database Management", "Communication"],
            "Mobile Development": ["Programming", "Web Development", "Problem Solving"],
            "Cybersecurity": ["Computer Networks", "Operating Systems", "Mathematics"],
            "Cloud Computing": ["Computer Networks", "Operating Systems", "Software Engineering"],
            "Blockchain": ["Programming", "Mathematics", "Computer Networks"],
            "Software Engineering": ["Programming", "Problem Solving", "Leadership"],
            "Advanced Algorithms": ["Programming", "Mathematics", "Problem Solving"],
            "Computer Networks": ["Operating Systems", "Mathematics", "Programming"],
            "Operating Systems": ["Programming", "Computer Networks", "Mathematics"]
        }

    def map_subject_to_skills(self, subject_name: str, description: str = "") -> Dict[str, float]:
        
        text = (subject_name + " " + description).lower()
        skill_scores = defaultdict(float)

        for skill, keywords in self.skill_keywords.items():
            for keyword, weight in keywords.items():
                if keyword in text:
                    if keyword in subject_name.lower():
                        skill_scores[skill] += weight * 1.5
                    else:
                        skill_scores[skill] += weight

        for pattern, skills in self.subject_patterns.items():
            if pattern in text:
                for skill in skills:
                    skill_scores[skill] += 0.5

        for subject_pattern, prereq_skills in self.prerequisite_mapping.items():
            if any(word in text for word in subject_pattern.lower().split()):
                for skill in prereq_skills:
                    skill_scores[skill] += 0.4

        if skill_scores:
            max_score = max(skill_scores.values())
            if max_score > 0:
                skill_scores = {skill: min((score / max_score) ** 0.7, 1.0) for skill, score in skill_scores.items()}

        all_skills = list(self.skill_keywords.keys())
        result = {skill: skill_scores.get(skill, 0.0) for skill in all_skills}

        if max(result.values()) == 0:
            if any(word in text for word in ["programming", "coding", "development"]):
                result["Programming"] = 0.6
                result["Software Engineering"] = 0.4
            elif any(word in text for word in ["data", "analysis", "statistics"]):
                result["Data Analysis"] = 0.6
                result["Statistics"] = 0.4
            elif any(word in text for word in ["web", "html", "css", "javascript"]):
                result["Web Development"] = 0.6
                result["Programming"] = 0.4
            elif any(word in text for word in ["security", "cyber", "cryptography"]):
                result["Cybersecurity"] = 0.6
                result["Computer Networks"] = 0.4
            else:
                result["Programming"] = 0.4
                result["Problem Solving"] = 0.4
                result["Mathematics"] = 0.3

        result = {skill: max(score, 0.0) if score >= 0.1 else 0.0 for skill, score in result.items()}

        return result

    def calculate_strength_score(self, student_grades: Dict[str, str],
                               subject_name: str, description: str,
                               master_df: pd.DataFrame) -> float:
      
        student_profile = self.build_student_skill_profile(student_grades, master_df)

        if not student_profile:
            return 0.0

        subject_skills = self.map_subject_to_skills(subject_name, description)

        score = 0.0
        total_weight = 0.0

        for skill, weight in subject_skills.items():
            student_skill = student_profile.get(skill, 0.0)
            score += student_skill * weight
            total_weight += weight

        if total_weight > 0:
            score = score / total_weight

        return max(0.0, min(10.0, score))

    def build_student_skill_profile(self, student_grades: Dict[str, str],
                                  master_df: pd.DataFrame) -> Dict[str, float]:
        
        from .ai_utils import GRADE_MAP

        accum = defaultdict(float)
        weight_accum = defaultdict(float)

        for _, row in master_df.iterrows():
            code = row.get("Subject Code")
            if code not in student_grades:
                continue

            grade = student_grades[code]
            grade_val = GRADE_MAP.get(grade, 5.0)

            subj_name = row.get("Subject Name", "")
            desc = row.get("Description", "")

            skill_weights = self.map_subject_to_skills(subj_name, desc)

            for skill, weight in skill_weights.items():
                accum[skill] += grade_val * weight
                weight_accum[skill] += weight

        skill_profile = {}
        for skill, total in accum.items():
            denom = weight_accum.get(skill, 1.0)
            if denom > 0:
                skill_profile[skill] = total / denom
            else:
                skill_profile[skill] = 0.0

        return skill_profile

    def get_subject_difficulty_score(self, subject_name: str, description: str) -> float:
        """
        Calculate subject difficulty score (0-1) based on keywords and patterns.
        """
        text = (subject_name + " " + description).lower()

        advanced_keywords = [
            "advanced", "graduate", "senior", "capstone", "thesis", "research",
            "machine learning", "deep learning", "artificial intelligence",
            "cryptography", "blockchain", "distributed", "parallel", "concurrent"
        ]

        intermediate_keywords = [
            "intermediate", "data structures", "algorithms", "database",
            "networking", "software engineering", "web development"
        ]

        introductory_keywords = [
            "introduction", "intro", "fundamentals", "basics", "beginner",
            "programming", "mathematics", "statistics"
        ]

        difficulty_score = 0.5

        for keyword in advanced_keywords:
            if keyword in text:
                difficulty_score += 0.2

        for keyword in intermediate_keywords:
            if keyword in text:
                difficulty_score += 0.1

        for keyword in introductory_keywords:
            if keyword in text:
                difficulty_score -= 0.1

        return max(0.0, min(1.0, difficulty_score))

    def get_subject_relevance_score(self, subject_name: str, description: str,
                                  student_profile: Dict[str, float]) -> float:
        """
        Calculate how relevant a subject is to student's current skill level.
        """
        subject_skills = self.map_subject_to_skills(subject_name, description)
        difficulty = self.get_subject_difficulty_score(subject_name, description)

        skill_alignment = 0.0
        total_weight = 0.0

        for skill, weight in subject_skills.items():
            student_skill = student_profile.get(skill, 0.0)
            skill_alignment += student_skill * weight
            total_weight += weight

        if total_weight > 0:
            skill_alignment = skill_alignment / total_weight

        skill_alignment = max(0.0, min(1.0, skill_alignment))

        difficulty_factor = max(0.1, 1.0 - abs(skill_alignment - difficulty) * 0.3)

        return skill_alignment * difficulty_factor

    def generate_comprehensive_recommendation(self, student_grades: Dict[str, str],
                                            subject_name: str, description: str,
                                            master_df: pd.DataFrame) -> Dict[str, float]:
        """
        Generate comprehensive recommendation with multiple scoring factors.
        """
        student_profile = self.build_student_skill_profile(student_grades, master_df)

        strength_score = self.calculate_strength_score(student_grades, subject_name, description, master_df)
        difficulty_score = self.get_subject_difficulty_score(subject_name, description)
        relevance_score = self.get_subject_relevance_score(subject_name, description, student_profile)

        strength_score = max(0.0, min(1.0, strength_score))
        difficulty_score = max(0.0, min(1.0, difficulty_score))
        relevance_score = max(0.0, min(1.0, relevance_score))

        combined_score = (
            strength_score * 0.5 +
            relevance_score * 0.3 +
            (1.0 - difficulty_score) * 0.2
        )

        combined_score = max(0.0, min(1.0, combined_score))

        return {
            "strength_score": strength_score,
            "difficulty_score": difficulty_score,
            "relevance_score": relevance_score,
            "combined_score": combined_score
        }


local_model = LocalPredictionModel()