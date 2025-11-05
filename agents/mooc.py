# pdf_rag_nvidia_deepseek_multirow.py
# ✅ Handles both subject-specific and department-wide MOOC queries.
# ✅ Outputs data row-wise per subject.

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# ───────────────────────────────────────────────
# 1️⃣ Initialize NVIDIA DeepSeek Model
# ───────────────────────────────────────────────
llm = ChatNVIDIA(
    model="deepseek-ai/deepseek-v3.1-terminus",
    api_key="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",
    temperature=0.1,
    top_p=0.7,
    max_completion_tokens=2048,
    extra_body={"chat_template_kwargs": {"thinking": True}},
)

# ───────────────────────────────────────────────
# 2️⃣ Load and Split PDF
# ───────────────────────────────────────────────
pdf_path = "uu.pdf"  
loader = PyPDFLoader(pdf_path)
documents = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
chunks = splitter.split_documents(documents)
print(f"✅ Loaded and split {len(chunks)} chunks from the PDF.")

# ───────────────────────────────────────────────
# 3️⃣ Embeddings + FAISS Store
# ───────────────────────────────────────────────
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

# ───────────────────────────────────────────────
# 4️⃣ Enhanced Prompt Template
# ───────────────────────────────────────────────
prompt = ChatPromptTemplate.from_template("""
You are a precise academic data extraction assistant.
You must extract MOOC course information from the provided PDF context.

If the question asks for a **single subject**, return only that subject’s details.
If the question asks for a **department** (e.g., "ECE", "HSS", "CSE"), return **all subjects under that department**, one block per subject.

Each subject must be printed in the following **row-wise format**:

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

Do NOT add explanations or commentary. Return only formatted results.

Context:
{context}

Question:
{question}
""")

# ───────────────────────────────────────────────
# 5️⃣ Helper to Join Retrieved Docs
# ───────────────────────────────────────────────
def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)

# ───────────────────────────────────────────────
# 6️⃣ Build RAG Chain
# ───────────────────────────────────────────────
rag_chain = (
    {"context": retriever | RunnableLambda(format_docs), "question": RunnablePassthrough()}
    | prompt
    | llm
)

# ───────────────────────────────────────────────
# 7️⃣ Interactive Chat
# ───────────────────────────────────────────────
print("\n🤖 DeepSeek (NVIDIA) Multi-Row PDF RAG ready! Type 'exit' to quit.\n")

while True:
    question = input("❓ Question: ")
    if question.lower() in ["exit", "quit"]:
        break

    answer = rag_chain.invoke(question)

    print("\n📋 Extracted Data:")
    print(answer.content.strip())
    print("\n" + "=" * 80 + "\n")
