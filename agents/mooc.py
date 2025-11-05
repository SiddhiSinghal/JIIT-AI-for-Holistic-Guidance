# agents/mooc.py
# ✅ NVIDIA DeepSeek PDF RAG integrated for Flask
# ✅ Converts your standalone script into a callable function

import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda


def run_pdf_mooc_query(question: str, pdf_path: str = None) -> str:
    """
    Runs DeepSeek NVIDIA RAG query to extract MOOC details from uu.pdf.
    Designed to be used inside Flask career_chat route.
    """

    # 🧩 Default PDF Path — absolute (never relative)
    if pdf_path is None:
        pdf_path = os.path.join(os.path.dirname(__file__), "uu.pdf")

    if not os.path.exists(pdf_path):
        return f"❌ PDF file not found at path: {os.path.abspath(pdf_path)}"

    try:
        # 1️⃣ Initialize NVIDIA DeepSeek model
        llm = ChatNVIDIA(
            model="deepseek-ai/deepseek-v3.1-terminus",
            api_key="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",
            temperature=0.1,
            top_p=0.7,
            max_completion_tokens=2048,
            extra_body={"chat_template_kwargs": {"thinking": True}},
        )

        # 2️⃣ Load and split PDF
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_documents(documents)

        # 3️⃣ Embedding + FAISS store
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(chunks, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

        # 4️⃣ Prompt
        prompt = ChatPromptTemplate.from_template("""
You are a precise academic data extraction assistant.
You must extract MOOC course information from the provided PDF context.

If the question asks for a single subject, return only that subject’s details.
If the question asks for a department (e.g., "ECE", "HSS", "CSE"), return all subjects under that department, one block per subject.

Each subject must be printed in the following format:
──────────────────────────────
Subject Name: <name>
Subject Code: <code>
MOOC Equivalent Course: <mooc course>
MOOC Code: <mooc code>
Credits: <credits>
NPTEL Link: <link>
Faculty: <faculty/coordinator name>
──────────────────────────────

If data for any field is not available, write "N/A".

Context:
{context}

Question:
{question}
""")

        def format_docs(docs):
            return "\n\n".join(d.page_content for d in docs)

        # 5️⃣ RAG chain
        rag_chain = (
            {"context": retriever | RunnableLambda(format_docs), "question": RunnablePassthrough()}
            | prompt
            | llm
        )

        # 6️⃣ Run once (for Flask request)
        result = rag_chain.invoke(question)
        return result.content.strip()

    except Exception as e:
        return f"⚠️ Error during MOOC extraction: {str(e)}"
