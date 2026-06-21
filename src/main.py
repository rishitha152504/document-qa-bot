"""Interactive Document Q&A Bot — Streamlit UI and CLI entry point."""

from __future__ import annotations

import sys

import streamlit as st

from src.config import DATA_DIR, DB_PATH, GEMINI_API_KEY, TOP_K
from src.ingest import ingest_documents
from src.query import is_database_ready, query_rag_pipeline


def run_cli() -> None:
    """Simple command-line Q&A loop."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not set. Create a .env file with your API key.")
        sys.exit(1)

    if not is_database_ready():
        print("Vector database not found. Running ingestion first...")
        ingest_documents()

    print("\nDocument Q&A Bot (type 'exit' or 'quit' to stop)\n")
    while True:
        question = input("Your question: ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break
        if not question:
            continue

        result = query_rag_pipeline(question)
        print(f"\nAnswer:\n{result['answer']}\n")
        if result["citations"]:
            print("Sources:")
            for cite in result["citations"]:
                print(f"  - {cite}")
        print()


def run_streamlit() -> None:
    """Streamlit web interface for the Document Q&A Bot."""
    st.set_page_config(
        page_title="Document Q&A Bot",
        page_icon="📚",
        layout="wide",
    )

    st.title("📚 Document Q&A Bot")
    st.markdown(
        "Ask questions about your documents. Answers are **grounded** in retrieved "
        "context with **source citations** — powered by RAG + Google Gemini."
    )

    try:
        streamlit_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        streamlit_key = ""
    api_key = GEMINI_API_KEY or streamlit_key
    if not api_key:
        st.error(
            "⚠️ **GEMINI_API_KEY** is not configured. "
            "Set it in `.env` locally or in Streamlit Cloud secrets."
        )
        st.stop()

    db_ready = is_database_ready()

    with st.sidebar:
        st.header("Settings")
        top_k = st.slider("Top-K chunks to retrieve", min_value=1, max_value=10, value=TOP_K)
        st.divider()
        st.subheader("Database")
        if db_ready:
            st.success("✅ Vector database is ready")
        else:
            st.warning("⚠️ Database not indexed yet")

        if st.button("🔄 Re-index Documents", use_container_width=True):
            with st.spinner("Indexing documents... This may take a minute."):
                try:
                    count = ingest_documents()
                    st.success(f"Indexed {count} chunks successfully!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Ingestion failed: {exc}")

        st.divider()
        st.caption(f"Data folder: `{DATA_DIR.name}/`")
        st.caption(f"DB path: `{DB_PATH}`")

    if not db_ready:
        st.info(
            "Click **Re-index Documents** in the sidebar to build the vector database "
            "from files in the `data/` folder, then ask your first question."
        )
        return

    question = st.text_input(
        "Ask a question about your documents",
        placeholder="e.g. What was the net revenue growth in FY2026?",
    )

    if st.button("Get Answer", type="primary") and question.strip():
        with st.spinner("Searching documents and generating answer..."):
            try:
                result = query_rag_pipeline(question.strip(), k=top_k)
            except Exception as exc:
                st.error(f"Query failed: {exc}")
                return

        st.subheader("Answer")
        st.markdown(result["answer"])

        if result["citations"]:
            st.subheader("Sources")
            for cite in result["citations"]:
                st.markdown(f"- **{cite}**")

        with st.expander("Retrieved context (debug)"):
            for idx, ctx in enumerate(result["raw_context"], start=1):
                st.markdown(f"**Chunk {idx}**")
                st.text(ctx[:800] + ("..." if len(ctx) > 800 else ""))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        run_cli()
    else:
        run_streamlit()
