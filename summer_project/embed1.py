from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
import json, os
from tqdm import tqdm
import pandas as pd


DATASETS = {
    "augesc": {
        "path": "augesc_train.json",
        "store": "chroma_augesc_store",
        "type": "jsonl"   
    },
    "counsel": {
        "path": "counsel_chat.xlsx",
        "store": "chroma_db_empathy",
        "type": "excel"  
    }
}

BATCH_SIZE = 256
PROGRESS_FILE = "progress.txt"

# === ChromaDB and Embedding Setup ===
model = SentenceTransformer("all-MiniLM-L6-v2")

def extract_usr_sys_pairs(convo_json_str):
    """Extract user + system messages from augesc dataset"""
    try:
        convo = json.loads(convo_json_str)
        user_lines = []
        last_sys = None
        for role, text in convo:
            if role == "usr":
                user_lines.append(text.strip())
            elif role == "sys":
                last_sys = text.strip()
        return " ".join(user_lines), last_sys
    except Exception as e:
        print(f"Error parsing conversation: {e}")
        return "", ""


def process_augesc(client, collection_name, dataset_path):
    print(f"\n=== Processing AugESC dataset: {dataset_path} ===")
    data = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    collection = client.get_or_create_collection(name=collection_name)
    start_index = 0
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            start_index = int(f.read().strip())

    for i in tqdm(range(start_index, len(data), BATCH_SIZE), desc="AugESC"):
        batch = data[i:i + BATCH_SIZE]
        ids, docs, metas = [], [], []

        for idx, item in enumerate(batch, start=i):
            user_text, assistant_text = extract_usr_sys_pairs(item["text"])
            if user_text and assistant_text:
                ids.append(f"augesc_{idx}")
                docs.append(user_text)
                metas.append({"response": assistant_text})

        if not docs:
            continue

        embeddings = model.encode(docs, convert_to_tensor=False).tolist()

        collection.add(
            ids=ids,
            documents=docs,
            embeddings=embeddings,
            metadatas=metas
        )

        with open(PROGRESS_FILE, "w") as f:
            f.write(str(i + BATCH_SIZE))

        print(f"Saved up to {i + len(docs)}")

    print("Finished AugESC dataset.")


def process_counsel(client, collection_name, dataset_path):
    print(f"\n=== Processing Counsel Chat dataset: {dataset_path} ===")
    df = pd.read_excel(dataset_path)

    # Assumption: Excel has columns "question" and "answer"
    # Adjust column names if needed
    questions = df["questionTitle"].astype(str).tolist()
    answers = df["questionText"].astype(str).tolist()

    collection = client.get_or_create_collection(name=collection_name)

    for i in tqdm(range(0, len(questions), BATCH_SIZE), desc="CounselChat"):
        batch_q = questions[i:i + BATCH_SIZE]
        batch_a = answers[i:i + BATCH_SIZE]

        ids = [f"counsel_{i+j}" for j in range(len(batch_q))]
        metas = [{"response": ans} for ans in batch_a]

        embeddings = model.encode(batch_q, convert_to_tensor=False).tolist()

        collection.add(
            ids=ids,
            documents=batch_q,
            embeddings=embeddings,
            metadatas=metas
        )

    print("Finished Counsel Chat dataset.")


if __name__ == "__main__":
    # Process both datasets
    for name, cfg in DATASETS.items():
        client = PersistentClient(path=cfg["store"])
        if cfg["type"] == "jsonl":
            process_augesc(client, name, cfg["path"])
        elif cfg["type"] == "excel":
            process_counsel(client, name, cfg["path"])

    print("\nAll datasets processed and embeddings stored.")
