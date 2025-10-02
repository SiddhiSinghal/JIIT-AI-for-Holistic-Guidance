import pickle
import pandas as pd
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# === Paths ===
here = os.path.dirname(__file__)
csv_path = os.path.join(here, "Student Placement.csv")  # replace with your CSV filename
model_path = os.path.join(here, "job_model.pkl")
encoder_path = os.path.join(here, "label_encoder.pkl")

# === Step 1: Load CSV ===
data = pd.read_csv(csv_path)

# === Step 2: Select numeric features ===
feature_cols = ['DSA','DBMS','OS','CN','Mathmetics','Aptitute','Comm',
                'Problem Solving','Creative','Hackathons']
X = data[feature_cols]

# === Step 3: Encode target labels ===
encoder = LabelEncoder()
y = encoder.fit_transform(data['Profile'])

# === Step 4: Train RandomForest model ===
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# === Step 5: Save model and encoder ===
with open(model_path, "wb") as f:
    pickle.dump(model, f)

with open(encoder_path, "wb") as f:
    pickle.dump(encoder, f)

print(f"✅ Model saved to {model_path}")
print(f"✅ Label encoder saved to {encoder_path}")
