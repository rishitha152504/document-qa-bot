"""Document ingestion pipeline: extract, chunk, embed, and persist to ChromaDB."""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
import google.generativeai as genai
from docx import Document as DocxDocument
from pypdf import PdfReader
from tqdm import tqdm

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    DB_PATH,
    EMBEDDING_MODEL,
    GEMINI_API_KEY,
)


def extract_pdf_pages(file_path: str) -> list[dict]:
    """Extract text page-by-page from a PDF with source metadata."""
    extracted_data: list[dict] = []
    file_name = os.path.basename(file_path)

    try:
        reader = PdfReader(file_path)

        for index, page in enumerate(reader.pages):
            text = page.extract_text()

            if text and text.strip():
                clean_text = " ".join(text.split())

                extracted_data.append(
                    {
                        "text": clean_text,
                        "metadata": {
                            "source": file_name,
                            "page": index + 1,
                        },
                    }
                )

    except Exception as exc:
        print(f"Error reading PDF {file_name}: {exc}")

    return extracted_data


def extract_docx_pages(file_path: str) -> list[dict]:
    """Extract text from a Word document."""
    extracted_data: list[dict] = []
    file_name = os.path.basename(file_path)

    try:
        doc = DocxDocument(file_path)

        paragraphs = [
            p.text.strip()
            for p in doc.paragraphs
            if p.text.strip()
        ]

        if paragraphs:
            full_text = "\n\n".join(paragraphs)
            clean_text = " ".join(full_text.split())

            extracted_data.append(
                {
                    "text": clean_text,
                    "metadata": {
                        "source": file_name,
                        "page": 1,
                    },
                }
            )

    except Exception as exc:
        print(f"Error reading DOCX {file_name}: {exc}")

    return extracted_data


def extract_txt_pages(file_path: str) -> list[dict]:
    """Extract text from a TXT file."""
    extracted_data: list[dict] = []
    file_name = os.path.basename(file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        if text.strip():
            clean_text = " ".join(text.split())

            extracted_data.append(
                {
                    "text": clean_text,
                    "metadata": {
                        "source": file_name,
                        "page": 1,
                    },
                }
            )

    except Exception as exc:
        print(f"Error reading TXT {file_name}: {exc}")

    return extracted_data


def extract_document(file_path: str) -> list[dict]:
    """Extract content based on file type."""

    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return extract_pdf_pages(file_path)

    if suffix == ".docx":
        return extract_docx_pages(file_path)

    if suffix == ".txt":
        return extract_txt_pages(file_path)

    print(f"Unsupported file type: {file_path}")
    return []


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks."""

    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunks.append(text[start:end])

        start += chunk_size - chunk_overlap

    return chunks


def chunk_extracted_pages(
    pages: list[dict],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Convert pages into chunks."""

    chunks = []

    for page in pages:
        text_chunks = split_text(
            page["text"],
            chunk_size,
            chunk_overlap,
        )

        for chunk_text in text_chunks:
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": page["metadata"],
                }
            )

    return chunks


def save_to_vector_db(
    chunks: list[dict],
    db_path: str = DB_PATH,
) -> None:
    """Embed chunks using Gemini and save to ChromaDB."""

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Please add it to your .env file."
        )

    # Configure Gemini
    genai.configure(api_key=GEMINI_API_KEY)

    # Create Chroma client
    client = chromadb.PersistentClient(path=db_path)

    # Remove old collection
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    # Create collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 20

    for start in tqdm(
        range(0, len(chunks), batch_size),
        desc="Indexing chunks",
    ):
        batch = chunks[start:start + batch_size]

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(batch):

            try:
                result = genai.embed_content(
                    model=EMBEDDING_MODEL,
                    content=chunk["text"],
                    task_type="retrieval_document",
                )

                embedding = result["embedding"]

                ids.append(f"id_{start + i}")
                documents.append(chunk["text"])
                embeddings.append(embedding)
                metadatas.append(chunk["metadata"])

            except Exception as exc:
                print(
                    f"Embedding failed for chunk "
                    f"{start + i}: {exc}"
                )

        if documents:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

    print(
        f"Successfully indexed "
        f"{len(chunks)} chunks."
    )


def ingest_documents(
    data_dir: Path | str = DATA_DIR,
    db_path: str = DB_PATH,
) -> int:
    """Complete ingestion pipeline."""

    data_path = Path(data_dir)

    if not data_path.exists():
        raise FileNotFoundError(
            f"Data directory not found: {data_path}"
        )

    supported = {".pdf", ".docx", ".txt"}

    files = sorted(
        f
        for f in data_path.iterdir()
        if f.is_file()
        and f.suffix.lower() in supported
    )

    if not files:
        raise FileNotFoundError(
            f"No supported documents found in {data_path}"
        )

    all_pages = []

    for file_path in tqdm(
        files,
        desc="Extracting documents",
    ):

        pages = extract_document(str(file_path))

        all_pages.extend(pages)

        print(
            f"{file_path.name}: "
            f"{len(pages)} page(s) extracted"
        )

    chunks = chunk_extracted_pages(all_pages)

    print(
        f"Created {len(chunks)} chunks "
        f"from {len(all_pages)} pages."
    )

    save_to_vector_db(chunks, db_path)

    return len(chunks)


if __name__ == "__main__":
    ingest_documents()
