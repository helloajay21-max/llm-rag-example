# rag_pipeline.py

from embeddings import get_embedding
from vector_store import VectorStore
from llm import get_llm_response
from chunking import chunk_text

# Global vector store
vector_store = VectorStore()


def ingest_documents(docs):
    """
    Ingest documents into vector store
    """
    all_chunks = []

    for doc in docs:
        chunks = chunk_text(doc)
        all_chunks.extend(chunks)

    if not all_chunks:
        return

    embeddings = [get_embedding(chunk) for chunk in all_chunks]

    vector_store.add(embeddings, all_chunks)


def query_rag(query):
    """
    Hybrid RAG:
    1. If no documents → normal LLM answer
    2. If docs exist → try RAG
    3. If no good match → fallback to LLM
    """

    # 👉 Case 1: No documents uploaded
    if len(vector_store.texts) == 0:
        return get_llm_response(query)

    # 👉 Case 2: Try RAG
    query_embedding = get_embedding(query)
    context_docs = vector_store.search(query_embedding)

    # 👉 If no relevant docs → fallback
    if not context_docs or len(context_docs) == 0:
        return get_llm_response(query)

    context = "\n".join(context_docs)

    # 👉 Smart hybrid prompt
    prompt = f"""
You are an intelligent assistant.

First, try to answer using the CONTEXT below.
If the context is not useful, you can answer using your own knowledge.

Context:
{context}

Question:
{query}
"""

    return get_llm_response(prompt)