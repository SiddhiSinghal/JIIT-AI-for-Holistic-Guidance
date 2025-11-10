import os
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import PromptTemplate

# === Load Embeddings and LLM ===
embedding = OllamaEmbeddings(model="nomic-embed-text")
llm = ChatOllama(
    model="llama3:instruct",
    temperature=0.3,
    num_predict=256,
    stream=False
)

vectorstore_augsec = Chroma(
    persist_directory="chroma_augesc_store",
    embedding_function=embedding
)

# Use forward slashes for compatibility
prompt_path = os.path.join(os.path.dirname(__file__), "templates/empathetic_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as f:
    template_text = f.read()

prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=template_text
)

def combined_qa_run(query, k_each=3):
    docs_augsec = vectorstore_augsec.similarity_search(query, k=k_each)
    combined_context = "\n\n".join(doc.page_content for doc in docs_augsec)
    final_prompt = prompt.format(context=combined_context, question=query)
    return llm.invoke(final_prompt).content

# 🔹 Wrapper function for Flask integration
def get_mental_health_response(prompt_text):
    """Generate a response for the mental health chat."""
    try:
        return combined_qa_run(prompt_text)
    except Exception as e:
        return f"⚠️ Error generating response: {e}"

__all__ = ["get_mental_health_response"]
