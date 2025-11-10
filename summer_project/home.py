import streamlit as st
from pymongo import MongoClient
import hashlib

client = MongoClient("mongodb://localhost:27017/")
db = client["mental_health_app"]
users_collection = db["users"]

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    if users_collection.find_one({"username": username}):
        return False
    users_collection.insert_one({"username": username, "password": hash_password(password)})
    return True

def authenticate_user(username, password):
    user = users_collection.find_one({"username": username})
    return user and user["password"] == hash_password(password)

st.set_page_config(page_title="Login - Coping Companion", layout="centered")

st.title(" Mental Health Coping Companion")
st.subheader(" Login or Create Account")

login_choice = st.radio("Choose an option:", ["Login", "Create Account"])
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if login_choice == "Create Account":
    if st.button("Create Account"):
        if username and password:
            if create_user(username, password):
                st.success(" Account created successfully! Please login.")
            else:
                st.error(" Username already taken.")
        else:
            st.warning("Please enter both username and password.")
else:
    if st.button("Login"):
        if username and password:
            if authenticate_user(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success(f"Welcome, {username}! Go to the Chat tab on the sidebar.")
            else:
                st.error(" Invalid username or password.")
        else:
            st.warning("Please enter both username and password.")
