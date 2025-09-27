# agents/job_recommendation.py
import os, pickle

MODEL_FILE = "job_model.pkl"
LE_FILE = "label_encoder.pkl"

def predict_jobs_from_list(user_vals):
    """
    If model files exist, return top 3 predictions; else fallback list
    user_vals: list of 10 numeric scores
    """
    if os.path.exists(MODEL_FILE) and os.path.exists(LE_FILE):
        try:
            with open(MODEL_FILE, "rb") as f:
                model = pickle.load(f)
            with open(LE_FILE, "rb") as f:
                le = pickle.load(f)
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba([user_vals])[0]
                import numpy as np
                top_idx = np.argsort(probs)[-3:][::-1]
                jobs = le.inverse_transform(top_idx).tolist()
            else:
                pred = model.predict([user_vals])
                jobs = le.inverse_transform(pred).tolist()
            return jobs
        except Exception as e:
            print("Model error:", e)
    # fallback
    fallback = ["Software Engineer", "Data Scientist", "Backend Developer", "Full Stack Developer", "ML Engineer"]
    return fallback[:3]
