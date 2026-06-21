"""Application configuration and constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = str(PROJECT_ROOT / "db")

# Gemini models
EMBEDDING_MODEL = "models/embedding-001"
GENERATION_MODEL = "gemini-2.0-flash"

# ChromaDB
COLLECTION_NAME = "document_knowledge_base"

# Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Retrieval
TOP_K = 5

# API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
