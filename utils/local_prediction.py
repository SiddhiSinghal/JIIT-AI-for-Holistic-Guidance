#!/usr/bin/env python3


import re
import math
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import pandas as pd
import numpy as np


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
