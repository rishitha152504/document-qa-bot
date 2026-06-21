"""Document ingestion pipeline: extract, chunk, embed, and persist to ChromaDB."""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
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
    """Extract text from a Word document, grouped by paragraph sections."""
    extracted_data: list[dict] = []
    file_name = os.path.basename(file_path)

    try:
        doc = DocxDocument(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            return extracted_data

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
    """Extract text from a plain text file."""
    extracted_data: list[dict] = []
    file_name = os.path.basename(file_path)

    try:
        with open(file_path, encoding="utf-8") as handle:
            text = handle.read()
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
    """Route extraction based on file extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_pages(file_path)
    if suffix == ".docx":
        return extract_docx_pages(file_path)
    if suffix == ".txt":
        return extract_txt_pages(file_path)
    print(f"Unsupported file type: {file_path}")
    return []


def _split_text_recursive(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str] | None = None,
) -> list[str]:
    """Recursively split text on natural boundaries (paragraphs, lines, spaces)."""
    if separators is None:
        separators = ["\n\n", "\n", " ", ""]

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    separator = separators[-1]
    for candidate in separators:
        if candidate == "" or candidate in text:
            separator = candidate
            break

    if separator:
        splits = text.split(separator)
    else:
        splits = list(text)

    chunks: list[str] = []
    current = ""

    for split in splits:
        piece = split if separator == "" else split + separator
        if len(current) + len(piece) <= chunk_size:
            current += piece
        else:
            if current.strip():
                chunks.append(current.strip())
            if len(piece) > chunk_size:
                next_separators = separators[separators.index(separator) + 1 :]
                sub_chunks = _split_text_recursive(
                    piece, chunk_size, chunk_overlap, next_separators
                )
                chunks.extend(sub_chunks)
                current = ""
            else:
                current = piece

    if current.strip():
        chunks.append(current.strip())

    # Apply overlap by merging tail of previous chunk into next when needed
    if chunk_overlap <= 0 or len(chunks) <= 1:
        return chunks

    overlapped: list[str] = [chunks[0]]
    for idx in range(1, len(chunks)):
        prev = overlapped[-1]
        overlap_text = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
        merged = f"{overlap_text} {chunks[idx]}".strip()
        overlapped.append(merged)

    return overlapped


def chunk_extracted_pages(
    pages: list[dict],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Split page-level documents into overlapping chunks with metadata."""
    chunks: list[dict] = []

    for page in pages:
        text = page["text"]
        metadata = page["metadata"]
        text_chunks = _split_text_recursive(text, chunk_size, chunk_overlap)

        for chunk_text in text_chunks:
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        "source": metadata["source"],
                        "page": metadata["page"],
                    },
                }
            )

    return chunks


def save_to_vector_db(chunks: list[dict], db_path: str = DB_PATH) -> None:
    """Embed text chunks and persist them in a local ChromaDB instance."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your .env file before ingesting."
        )

    client = chromadb.PersistentClient(path=db_path)
    embedding_fn = GoogleGenerativeAiEmbeddingFunction(
        api_key=GEMINI_API_KEY,
        model_name=EMBEDDING_MODEL,
    )

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 50
    for start in tqdm(range(0, len(chunks), batch_size), desc="Indexing chunks"):
        batch = chunks[start : start + batch_size]
        ids = [f"id_{start + i}" for i in range(len(batch))]
        documents = [chunk["text"] for chunk in batch]
        metadatas = [chunk["metadata"] for chunk in batch]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"Successfully indexed {len(chunks)} chunks in the vector database.")


def ingest_documents(data_dir: Path | str = DATA_DIR, db_path: str = DB_PATH) -> int:
    """Full ingestion pipeline: scan data folder, extract, chunk, and index."""
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    supported = {".pdf", ".docx", ".txt"}
    files = sorted(
        f for f in data_path.iterdir() if f.is_file() and f.suffix.lower() in supported
    )

    if not files:
        raise FileNotFoundError(f"No supported documents found in {data_path}")

    all_pages: list[dict] = []
    for file_path in tqdm(files, desc="Extracting documents"):
        pages = extract_document(str(file_path))
        all_pages.extend(pages)
        print(f"  {file_path.name}: {len(pages)} page(s) extracted")

    chunks = chunk_extracted_pages(all_pages)
    print(f"Created {len(chunks)} chunks from {len(all_pages)} page(s).")

    save_to_vector_db(chunks, db_path=db_path)
    return len(chunks)


if __name__ == "__main__":
    ingest_documents()
