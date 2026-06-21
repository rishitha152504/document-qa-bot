"""RAG query pipeline: similarity search and grounded answer generation."""

from __future__ import annotations

import chromadb
import google.generativeai as genai

from src.config import (
    COLLECTION_NAME,
    DB_PATH,
    EMBEDDING_MODEL,
    GEMINI_API_KEY,
    GENERATION_MODEL,
    TOP_K,
)

SYSTEM_PROMPT = (
    "You are a professional, accurate document Q&A assistant. "
    "Answer the user's question using ONLY the provided document context below. "
    "Cite the sources (filenames and pages) inline next to facts you cite, "
    "for example: (Source: annual_report.pdf, Page: 12). "
    "If the answer cannot be found in the context, clearly state: "
    "'I am sorry, but the provided documents do not contain the answer to your question.' "
    "Do not make up facts or use external knowledge sources."
)


def _get_collection(db_path: str = DB_PATH):
    """Load the ChromaDB collection."""

    client = chromadb.PersistentClient(path=db_path)

    return client.get_collection(
        name=COLLECTION_NAME
    )


def query_rag_pipeline(
    user_query: str,
    db_path: str = DB_PATH,
    k: int = TOP_K,
) -> dict:
    """Search vector DB and generate grounded answer."""

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not configured."
        )

    genai.configure(api_key=GEMINI_API_KEY)

    collection = _get_collection(db_path)

    # Create embedding for user query
    embedding_response = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=user_query,
        task_type="retrieval_query",
    )

    query_embedding = embedding_response["embedding"]

    # Search similar chunks
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
    )

    if (
        not results["documents"]
        or not results["documents"][0]
    ):
        return {
            "answer": (
                "I am sorry, but the provided documents "
                "do not contain the answer to your question."
            ),
            "citations": [],
            "raw_context": [],
        }

    context_blocks = []
    citations = []

    for doc, meta in zip(
        results["documents"][0],
        results["metadatas"][0],
    ):

        source_name = meta.get("source", "unknown")
        page_num = meta.get("page", "?")

        citation = (
            f"Source: {source_name}, "
            f"Page: {page_num}"
        )

        context_blocks.append(
            f"[{citation}]\nContext: {doc}"
        )

        citations.append(citation)

    context_payload = "\n\n---\n\n".join(context_blocks)

    prompt = f"""
{SYSTEM_PROMPT}

CONTEXT INFORMATION:
{context_payload}

USER QUESTION:
{user_query}

GROUNDED ANSWER:
"""

    model = genai.GenerativeModel(
        GENERATION_MODEL
    )

    response = model.generate_content(prompt)

    answer = (
        response.text
        if hasattr(response, "text")
        else "No response generated."
    )

    return {
        "answer": answer,
        "citations": list(dict.fromkeys(citations)),
        "raw_context": results["documents"][0],
    }


def is_database_ready(
    db_path: str = DB_PATH
) -> bool:
    """Check whether vector DB exists."""

    try:
        collection = _get_collection(db_path)

        return collection.count() > 0

    except Exception:
        return False
