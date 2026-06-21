# Document Q&A Bot with RAG

A production-ready **Retrieval-Augmented Generation (RAG)** system that lets you ask natural-language questions about your private documents (PDF, DOCX, TXT) and receive **grounded answers with source citations**.

Built with **Python 3.11+**, **ChromaDB**, and **Google Gemini**.

## Features

- **Multi-format ingestion** — PDF, DOCX, and TXT with page-level metadata
- **Recursive text chunking** — Splits on paragraphs, lines, and words with configurable overlap
- **Persistent vector store** — ChromaDB saved to disk; index once, query instantly
- **Semantic search** — Gemini `text-embedding-004` embeddings with cosine similarity
- **Grounded answers** — Strict system prompt prevents hallucinations
- **Inline citations** — Every answer references source file and page number
- **Streamlit UI** — Interactive web interface (bonus)
- **CLI mode** — Command-line Q&A loop

## Architecture

```
Custom Documents (PDF, DOCX, TXT)
         │
         ▼
  Document Ingestion (ingest.py)
         │
         ▼
  Recursive Chunking + Embeddings
         │
         ▼
  ChromaDB (db/) — Persistent Vector Store
         │
         ▼
  User Query → Similarity Search (query.py)
         │
         ▼
  Prompt + Retrieved Context → Gemini LLM
         │
         ▼
  Grounded Answer + Citations
```

## Project Structure

```
document-qa-bot/
├── .env                  # API keys (not committed)
├── .gitignore
├── README.md
├── requirements.txt
├── app.py                # Streamlit Cloud entry point
├── data/                 # Source documents
│   ├── business_doc.pdf
│   ├── science_paper.pdf
│   ├── factsheet.docx
│   ├── company_policy.txt
│   └── technical_faq.txt
├── db/                   # ChromaDB persistent storage
├── scripts/
│   └── generate_sample_docs.py
└── src/
    ├── config.py         # Configuration & constants
    ├── ingest.py         # Extract, chunk, embed, save
    ├── query.py          # Search & generate answers
    └── main.py           # Streamlit UI & CLI
```

## Quick Start

### 1. Clone & set up environment

```bash
git clone https://github.com/YOUR_USERNAME/document-qa-bot.git
cd document-qa-bot
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API key

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and set your Google Gemini API key:

```
GEMINI_API_KEY=your_key_here
```

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Generate sample documents (optional)

```bash
python scripts/generate_sample_docs.py
```

### 4. Index documents

```bash
python -m src.ingest
```

### 5. Run the app

**Streamlit UI:**

```bash
streamlit run app.py
```

**CLI mode:**

```bash
python -m src.main --cli
```

## Example Questions

Try these after indexing the sample documents:

- *What was Acme Corporation's net revenue growth in FY2026?*
- *What chunking strategy performed best in the research paper?*
- *What are the pricing tiers for the Acme Analytics Platform?*
- *What is the home office stipend for remote employees?*
- *What databases does the Analytics Platform support?*

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select this repository
4. Set **Main file path** to `app.py`
5. Add secret: `GEMINI_API_KEY = "your_key"`
6. Deploy

> **Note:** For cloud deployment, run ingestion locally and commit the `db/` folder, or use the **Re-index Documents** button in the sidebar (requires API key in secrets).

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| PDF parsing | pypdf |
| DOCX parsing | python-docx |
| Vector DB | ChromaDB (local, persistent) |
| Embeddings | Gemini `text-embedding-004` |
| LLM | Gemini `gemini-2.0-flash` |
| UI | Streamlit |
| Config | python-dotenv |

## License

MIT
