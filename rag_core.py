"""
RAG core: chunking, Gemini embeddings, Chroma vector store, Groq generation.
"""
import os
import warnings
from typing import Any

warnings.filterwarnings("ignore", message=".*google.generativeai.*", category=FutureWarning)
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
from groq import Groq

from config import (
    CHROMA_PATH,
    CHROMA_COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K,
    SIMILARITY_THRESHOLD,
    EMBEDDING_MODEL,
    GENERATION_MODEL,
)

_gemini_configured = False
_groq_client: Groq | None = None


def configure_gemini() -> None:
    global _gemini_configured
    if _gemini_configured:
        return
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("Set GEMINI_API_KEY or GOOGLE_API_KEY")
    genai.configure(api_key=key)
    _gemini_configured = True


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise ValueError("Set GROQ_API_KEY")
        _groq_client = Groq(api_key=key)
    return _groq_client


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks with optional overlap. Prefer word boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks


def get_embedding(text: str) -> list[float]:
    """Single text -> embedding via Gemini."""
    configure_gemini()
    result = genai.embed_content(model=EMBEDDING_MODEL, content=text)
    if "embedding" in result:
        return result["embedding"]
    if "embeddings" in result and result["embeddings"]:
        emb = result["embeddings"]
        return emb[0] if isinstance(emb, list) else emb
    raise ValueError("Unexpected embed_content result shape")


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch embed (one API call per item for Gemini; can be optimized later)."""
    return [get_embedding(t) for t in texts]


class GeminiEmbeddingFunction:
    """Chroma embedding function using Gemini."""

    def name(self) -> str:
        return "gemini"

    def __call__(self, input: list[str]) -> list[list[float]]:
        return get_embeddings(input)

    def embed_query(self, input: str | list[str]) -> list[list[float]]:
        """Used by Chroma when querying. Returns list of one vector so query_embeddings is [[...]]."""
        if isinstance(input, list) and input:
            input = input[0]
        emb = get_embedding(str(input))
        return [emb]


def get_chroma_client():
    """Persistent Chroma client."""
    os.makedirs(CHROMA_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))


def get_collection():
    """Get or create the RAG collection with Gemini embeddings."""
    configure_gemini()
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=GeminiEmbeddingFunction(),
        metadata={"description": "RAG chunks"},
    )


def clear_collection():
    """Delete the RAG collection. Next get_collection() will create a new empty one."""
    client = get_chroma_client()
    try:
        client.delete_collection(name=CHROMA_COLLECTION_NAME)
    except Exception:
        pass


def delete_chunks_by_source(source_value: str) -> None:
    """Delete all chunks whose metadata 'source' equals source_value."""
    coll = get_collection()
    try:
        coll.delete(where={"source": {"$eq": source_value}})
    except Exception:
        pass


def add_chunks_to_collection(chunks: list[str], metadatas: list[dict[str, Any]] | None = None, ids: list[str] | None = None):
    """Add chunk texts (and optional metadatas/ids) to Chroma. IDs default to chunk index."""
    if not chunks:
        return
    coll = get_collection()
    if ids is None:
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]
    if metadatas is None:
        metadatas = [{}] * len(chunks)
    # Chroma metadata values must be str, int, float, or bool
    safe_metadatas = []
    for m in metadatas:
        safe = {}
        for k, v in m.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                safe[k] = v
            else:
                safe[k] = str(v)
        safe_metadatas.append(safe)
    coll.add(documents=chunks, metadatas=safe_metadatas, ids=ids)


def query_collection(query_text: str, n_results: int = TOP_K):
    """Return top-n chunks with metadata and distances (lower = more similar)."""
    coll = get_collection()
    result = coll.query(
        query_texts=[query_text],
        n_results=min(n_results, 100),
        include=["documents", "metadatas", "distances"],
    )
    docs = result["documents"][0] if result["documents"] else []
    metas = result["metadatas"][0] if result["metadatas"] else []
    dists = result["distances"][0] if result["distances"] else []
    # Chroma returns L2 distance; convert to similarity-like (0 = best). We use 1/(1+d) as proxy for similarity for thresholding.
    return list(zip(docs, metas, dists))


def query_rag(question: str) -> dict[str, Any]:
    """
    Run RAG: retrieve top chunks, build prompt, call Groq. Return answer and sources.
    If retrieval is below threshold, return a safe "I don't have enough information" answer.
    """
    question = (question or "").strip()
    if not question:
        return {"answer": "Please ask a question.", "sources": []}

    configure_gemini()
    groq = get_groq_client()

    results = query_collection(question, n_results=TOP_K)
    if not results:
        return {
            "answer": "I couldn't find any relevant information in the knowledge base to answer that.",
            "sources": [],
        }

    # Chroma L2 distance: lower is better. Use first result's distance as "best". Threshold in L2 terms (e.g. > 1.5 = weak).
    best_distance = results[0][2] if results else float("inf")
    # Heuristic: if best distance is high, consider it no match (depends on embedding scale)
    if best_distance > 2.0:  # tune as needed for Gemini embedding scale
        return {
            "answer": "I couldn't find relevant information in the knowledge base for that question.",
            "sources": [],
        }

    top_chunks = [r[0] or "" for r in results]
    metadatas = [r[1] or {} for r in results]
    context = "\n\n".join(top_chunks)
    source_labels = []
    for i, meta in enumerate(metadatas):
        if not isinstance(meta, dict):
            meta = {}
        label = meta.get("source") or meta.get("url") or meta.get("filename") or f"Chunk {i+1}"
        chunk_text = top_chunks[i] if i < len(top_chunks) else ""
        snippet = (chunk_text[:200] + "...") if len(chunk_text) > 200 else chunk_text
        source_labels.append({"text": snippet, "source": str(label)})

    prompt = f"""Answer the question using ONLY the context below. If the context does not contain enough information, say: "I don't have enough information in the knowledge base to answer that."
Do not guess or use external knowledge. Keep the answer concise. If possible, quote the relevant part of the context.

Context:
{context}

Question:
{question}
"""

    try:
        response = groq.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = (response.choices[0].message.content or "").strip() if response.choices else ""
    except Exception as e:
        answer = f"Sorry, an error occurred while generating an answer: {str(e)}"

    return {"answer": answer or "I couldn't generate an answer.", "sources": source_labels}
