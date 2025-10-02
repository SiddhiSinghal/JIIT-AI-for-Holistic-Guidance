# job_recommendation.py
import pickle
import pandas as pd
from models import UserScores
from flask_login import current_user

def load_model_and_encoder():
    with open("agents/job_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open("agents/label_encoder.pkl", "rb") as f:
        encoder = pickle.load(f)
    return model, encoder

def recommend_jobs():
    model, encoder = load_model_and_encoder()

    # fetch latest scores of current user
    latest = (
        UserScores.query
        .filter_by(user_id=current_user.id)
        .order_by(UserScores.timestamp.desc())
        .first()
    )

    if not latest:
        return []  # return empty list if no scores

    features = [
        latest.dsa, latest.dbms, latest.os,
        latest.cn, latest.math, latest.aptitude,
        latest.comm, latest.problem_solving,
        latest.creative, latest.hackathons
    ]

    # Convert to DataFrame to match training features
    columns = ["DSA","DBMS","OS","CN","Mathmetics","Aptitute","Comm",
               "Problem Solving","Creative","Hackathons"]
    features_df = pd.DataFrame([features], columns=columns)

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features_df)[0]
        top_3_indices = probabilities.argsort()[-3:][::-1]
        top_3_jobs = encoder.inverse_transform(top_3_indices).tolist()
    else:
        pred = model.predict(features_df)
        top_3_jobs = encoder.inverse_transform(pred).tolist()

    # ✅ Return a list instead of formatted string
    return top_3_jobs
