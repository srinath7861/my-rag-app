"""Shared config for RAG, ingestion, and API."""
import os

# Paths
CHROMA_PATH = os.environ.get("CHROMA_PATH", os.path.join(os.path.dirname(__file__), "chroma_db"))
KNOWLEDGE_PATH = os.environ.get("KNOWLEDGE_PATH", "knowledge.txt")
URL_CONTENT_PATH = os.environ.get("URL_CONTENT_PATH", "url_content.txt")
QNA_PATH = os.environ.get("QNA_PATH", "qna.txt")
DOCUMENTS_DIR = os.environ.get("DOCUMENTS_DIR", "documents")

# Chunking
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "50"))

# Retrieval
TOP_K = int(os.environ.get("TOP_K", "5"))
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.4"))

# Models
EMBEDDING_MODEL = "models/gemini-embedding-001"
GENERATION_MODEL = "llama-3.3-70b-versatile"
CHROMA_COLLECTION_NAME = "rag_chunks"
