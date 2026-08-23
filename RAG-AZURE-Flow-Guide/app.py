# app.py

import streamlit as st
from rag_pipeline import ingest_documents, query_rag
from document_loader import load_documents

st.set_page_config(page_title="Advanced RAG App", layout="wide")

st.title("🚀 Advanced RAG App (PDF + TXT + Azure Key Vault)")

# Upload
uploaded_files = st.file_uploader(
    "Upload documents (PDF or TXT)",
    type=["pdf", "txt"],
    accept_multiple_files=True
)

if uploaded_files:
    docs = load_documents(uploaded_files)
    ingest_documents(docs)
    st.success("✅ Documents processed successfully!")

# Query
query = st.text_input("Ask your question:")

if st.button("Ask"):
    if not query:
        st.warning("Enter a question")
    else:
        answer = query_rag(query)
        st.write("### 🤖 Answer")
        st.write(answer)