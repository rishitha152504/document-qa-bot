# Document Q&A Bot — Project Analysis

## Overview

This project implements a **Retrieval-Augmented Generation (RAG)** pipeline that enables question answering over private documents. Instead of relying solely on the LLM's pre-trained knowledge, the system retrieves relevant document chunks at query time and grounds the model's response in that retrieved context.

## Problem Statement

Large Language Models have two critical limitations for enterprise use:

1. **Knowledge cutoffs** — They cannot access private or recent documents.
2. **Hallucinations** — They may invent plausible but incorrect answers when context is missing.

RAG mitigates both by injecting semantically relevant document excerpts into the prompt before generation.

## Architecture

| Stage | Module | Description |
|-------|--------|-------------|
| Ingestion | `src/ingest.py` | Extracts text from PDF, DOCX, TXT with page metadata |
| Chunking | `src/ingest.py` | Recursive character splitting (1000 chars, 200 overlap) |
| Embedding | ChromaDB + Gemini | `text-embedding-004` with cosine similarity |
| Storage | `db/` | Persistent local ChromaDB — index once, query many times |
| Retrieval | `src/query.py` | Top-k semantic search (default k=5) |
| Generation | `src/query.py` | Gemini 2.0 Flash with strict grounding prompt |
| UI | `src/main.py` / `app.py` | Streamlit web app + CLI mode |

## Design Decisions

### Recursive Chunking
Fixed-size splits can break sentences mid-thought. Recursive splitting tries paragraph breaks (`\n\n`), line breaks (`\n`), and spaces before hard-cutting, preserving semantic coherence.

### Chunk Overlap (200 chars)
Overlap ensures facts at chunk boundaries appear in multiple segments, improving retrieval recall.

### Strict Grounding Prompt
The system prompt explicitly forbids external knowledge and requires the model to admit when context is insufficient — reducing hallucination rates.

### Separation of Concerns
- `ingest.py` — One-time indexing pipeline
- `query.py` — Runtime search and answer generation
- `main.py` — User interface layer

## Sample Documents

Five documents in `data/` covering business, research, product, policy, and technical FAQ content:

- `business_doc.pdf` — Acme Corp FY2026 annual report (3 pages)
- `science_paper.pdf` — RAG research paper (3 pages)
- `factsheet.docx` — Product factsheet with pricing
- `company_policy.txt` — Remote work policy
- `technical_faq.txt` — Platform technical FAQ

## Evaluation Questions

| Question | Expected Source |
|----------|----------------|
| What was net revenue growth in FY2026? | business_doc.pdf, Page 1 (14%) |
| Best chunking strategy in the paper? | science_paper.pdf (recursive, k=5) |
| Pricing for Business Plan? | factsheet.docx ($89/user/month) |
| Home office stipend amount? | company_policy.txt ($500) |
| Supported databases? | technical_faq.txt (PostgreSQL, MySQL, etc.) |

## Tech Stack

- Python 3.11+
- pypdf, python-docx — Document parsing
- ChromaDB — Local vector database
- Google Gemini — Embeddings + generation
- Streamlit — Web UI
- python-dotenv — Environment management

## Deployment

The app is deployed on **Streamlit Community Cloud** with the Gemini API key stored as a Streamlit secret. The pre-indexed vector database in `db/` enables instant Q&A without re-embedding on startup.

## Future Improvements

- Hybrid sparse + dense retrieval for better keyword matching
- Multi-hop retrieval for complex questions
- Automatic citation verification
- Document upload UI for dynamic indexing
