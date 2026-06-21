"""RAG query pipeline: similarity search and grounded answer generation."""

from __future__ import annotations

import google.generativeai as genai
import chromadb
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction

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
    """Load the ChromaDB collection with Gemini embeddings."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your .env file or Streamlit secrets."
        )

    client = chromadb.PersistentClient(path=db_path)
    embedding_fn = GoogleGenerativeAiEmbeddingFunction(
        api_key=GEMINI_API_KEY,
        model_name=EMBEDDING_MODEL,
    )
    return client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )


def query_rag_pipeline(
    user_query: str,
    db_path: str = DB_PATH,
    k: int = TOP_K,
) -> dict:
    """Search the vector DB, build a grounded prompt, and query Gemini."""
    collection = _get_collection(db_path)

    results = collection.query(query_texts=[user_query], n_results=k)

    if not results["documents"] or not results["documents"][0]:
        return {
            "answer": (
                "I am sorry, but the provided documents do not contain "
                "the answer to your question."
            ),
            "citations": [],
            "raw_context": [],
        }

    context_blocks: list[str] = []
    citations: list[str] = []

    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        source_name = meta.get("source", "unknown")
        page_num = meta.get("page", "?")
        citation_str = f"Source: {source_name}, Page: {page_num}"

        context_blocks.append(f"[{citation_str}]\nContext: {doc}")
        citations.append(citation_str)

    context_payload = "\n\n---\n\n".join(context_blocks)

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"CONTEXT INFORMATION:\n{context_payload}\n\n"
        f"USER QUESTION: {user_query}\n\n"
        f"GROUNDED ANSWER:"
    )

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GENERATION_MODEL)
    response = model.generate_content(prompt)

    return {
        "answer": response.text,
        "citations": list(dict.fromkeys(citations)),
        "raw_context": results["documents"][0],
    }


def is_database_ready(db_path: str = DB_PATH) -> bool:
    """Check whether the vector database has been indexed."""
    try:
        collection = _get_collection(db_path)
        return collection.count() > 0
    except Exception:
        return False
