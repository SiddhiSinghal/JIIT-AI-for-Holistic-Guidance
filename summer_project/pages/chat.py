import streamlit as st
import datetime
import os
import torch
from pymongo import MongoClient
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document
from langchain.chat_models import ChatOllama
from sentence_transformers import SentenceTransformer, util
from rag_chain import combined_qa_run, vectorstore_augsec

# === Setup ===
current_dir = os.path.dirname(__file__)
prompt_path = os.path.join(current_dir, "empathetic_prompt.txt")

with open(prompt_path, "r", encoding="utf-8") as f:
    PROMPT_TEMPLATE = f.read()

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
embedding_model.to(torch.device("cpu"))

SIMILARITY_THRESHOLD = 0.8
MAX_RETRIES = 3

client = MongoClient("mongodb://localhost:27017/")
db = client["mental_health_bot"]
summary_collection = db["user_summaries"]
feedback_collection = db["feedback"]

llm = ChatOllama(model="llama3:instruct", temperature=0.7, num_ctx=2048)
summarize_chain = load_summarize_chain(llm, chain_type="stuff")

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "self harm", "end my life", "want to die",
    "hurting myself", "cutting", "hopeless", "no reason to live"
]

def check_crisis(text):
    return any(keyword in text.lower() for keyword in CRISIS_KEYWORDS)

def is_similar_to_bad_feedback(prompt, response):
    combined_input = f"{prompt} {response}"
    new_embedding = embedding_model.encode(combined_input, convert_to_tensor=True)

    for entry in feedback_collection.find({"feedback": "bad", "embedding": {"$exists": True}}):
        bad_embedding = torch.tensor(entry["embedding"])
        similarity = util.cos_sim(new_embedding, bad_embedding).item()
        if similarity > SIMILARITY_THRESHOLD:
            return True
    return False

def generate_and_store_summary(user_id, conversation):
    conversation_text = "\n".join([msg["content"] for msg in conversation if msg["role"] == "user"])
    if not conversation_text.strip():
        return
    docs = [Document(page_content=conversation_text)]
    summary = summarize_chain.run(docs)
    summary_collection.update_one(
        {"user_id": user_id},
        {"$set": {"summary": summary, "last_updated": datetime.datetime.utcnow()}},
        upsert=True
    )

def get_recent_user_history(n=2):
    history = [msg["content"] for msg in st.session_state.messages[-n*2:] if msg["role"] == "user"]
    return "\n".join(history)

def enhanced_qa_run(context, user_question):
    history_context = get_recent_user_history()
    full_context = f"{context}\n\nRecent messages:\n{history_context}"
    prompt_text = PROMPT_TEMPLATE.format(context=full_context, question=user_question)

    for attempt in range(MAX_RETRIES):
        response = combined_qa_run(prompt_text)
        if is_similar_to_bad_feedback(user_question, response):
            st.warning(" Detected response similar to previously flagged bad feedback. Retrying...")
        else:
            return response

    st.error(" Couldn't generate a completely new response after several tries. Returning last attempt.")
    return response

# === Streamlit UI ===
st.set_page_config(page_title=" Mental Health Coping Companion", layout="wide")

st.title(" MentBOT")

if not st.session_state.get("logged_in"):
    st.warning(" Please log in from the Home page.")
    st.stop()

user_id = st.session_state["username"]
stored_summary = summary_collection.find_one({"user_id": user_id}) or {}
stored_summary_text = stored_summary.get("summary", "")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "feedback_store" not in st.session_state:
    st.session_state.feedback_store = {}
if "last_input" not in st.session_state:
    st.session_state.last_input = None
    st.session_state.last_retrieved_docs_augsec = []

if "pending_user_input" in st.session_state:
    pending_input = st.session_state.pop("pending_user_input")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({"role": "user", "content": pending_input, "time": timestamp})

    if check_crisis(pending_input):
        st.session_state.messages.append({"role": "assistant", "content": "** Crisis Detected:** Please contact a professional.", "time": timestamp})
    else:
        with st.spinner(" Generating response..."):
            context_text = stored_summary_text
            response = enhanced_qa_run(context_text, pending_input)

        st.session_state.messages.append({"role": "assistant", "content": response, "time": timestamp})
        st.session_state.feedback_store[pending_input] = {"response": response, "submitted": False}
        st.session_state.last_input = pending_input
        st.session_state.last_retrieved_docs_augsec = vectorstore_augsec.similarity_search(pending_input, k=3)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        st.markdown(f"<div class='timestamp'>{msg['time']}</div>", unsafe_allow_html=True)

pending_feedback = {k: v for k, v in st.session_state.feedback_store.items() if not v["submitted"]}

if pending_feedback:
    
    for question, data in pending_feedback.items():
        
        retrieved_context = "\n\n".join([
            doc.page_content for doc in st.session_state.last_retrieved_docs_augsec
        ])

        col1, col2, _ = st.columns([1, 1, 8])

        def save_feedback(feedback_type):
            combined_text = f"{question} {data['response']}"
            embedding = embedding_model.encode(combined_text).tolist()

            feedback_data = {
                "user": user_id,
                "question": question,
                "response": data["response"],
                "retrieved_context": retrieved_context,
                "feedback": feedback_type,
                "embedding": embedding
            }
            feedback_collection.insert_one(feedback_data)
            st.session_state.feedback_store[question]["submitted"] = True
            st.success(" Feedback saved!")
            st.rerun()

        with col1:
            if st.button("👍 Good", key=f"good_{hash(question)}"):
                save_feedback("good")
        with col2:
            if st.button("👎 Bad", key=f"bad_{hash(question)}"):
                save_feedback("bad")

        st.markdown("---")

user_input = st.chat_input("Type your message here...")
if user_input:
    st.session_state.pending_user_input = user_input
    st.rerun()



with st.sidebar:
    st.header(" Session Options")

    if st.button(" Save Summary"):
        generate_and_store_summary(user_id, st.session_state.messages)
        st.success(" Summary saved.")
        st.session_state.clear()
        st.rerun()

    if st.button(" Logout"):
        st.session_state.clear()
        st.rerun()

    with st.expander(" Debug Info"):
        st.write("Session State Keys:", list(st.session_state.keys()))
