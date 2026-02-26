# RAG System – Vector DB, Ingestion, API & Website

RAG pipeline with **Chroma** vector DB, **Gemini** embeddings, **Groq** generation. Ingest **PDF, DOCX, and URLs**; query via **HTTP API** or **CLI**; use the built-in **chat UI** in the browser.

## What’s included

- **RAG pipeline** – Chunking (with overlap), Gemini embeddings, Chroma vector store, Groq generation, similarity threshold and source citations.
- **Vector DB** – Chroma (persistent in `chroma_db/`). Replace with pgvector on RDS for AWS scale.
- **Ingestion** – PDF (pypdf), DOCX (python-docx), URL (requests + BeautifulSoup). Same chunking and embedding as the rest of the app.
- **HTTP API** – FastAPI: `POST /query`, `POST /ingest/url`, `POST /ingest/document` (file upload), `GET /health`. Optional static chat UI at `/`.
- **Website** – Simple chat page served at `http://localhost:8000/` when the API runs.
- **AWS** – Runs on EC2 + Chroma (or later pgvector on RDS). See **STEPS.md** for deployment.

## Quick start

1. **Install:** `pip install -r requirements.txt`
2. **Set keys:** `GEMINI_API_KEY` and `GROQ_API_KEY` (see STEPS.md).
3. **Ingest:** e.g. `python -c "from ingest import ingest_knowledge_file; ingest_knowledge_file()"`
4. **Run API:** `python api.py` → open http://localhost:8000/
5. **Or CLI:** `python rag.py`

**Full instructions and AWS deployment:** see **[STEPS.md](STEPS.md)**.

## Project layout

| File / folder   | Purpose |
|-----------------|--------|
| `config.py`     | Shared config (chunk size, top-k, paths, model names). |
| `rag_core.py`   | Chunking, Gemini embeddings, Chroma get/add/query, `query_rag()`. |
| `ingest.py`     | Extract text from PDF/DOCX/URL; chunk and add to Chroma. |
| `api.py`        | FastAPI app: /query, /ingest/url, /ingest/document, /health, serves `/` chat UI. |
| `rag.py`        | CLI: interactive Q&A using the same Chroma + Gemini + Groq. |
| `static/`       | Chat UI (index.html). |
| `chroma_db/`    | Chroma data (created on first ingest). |
| `STEPS.md`      | Step-by-step run and AWS deploy. |

## API summary

- **POST /query** – Body: `{"question": "..."}`. Returns `{"answer": "...", "sources": [...]}`.
- **POST /ingest/url** – Body: `{"url": "https://..."}`. Ingests that URL.
- **POST /ingest/document** – Multipart file (PDF or DOCX). Ingests the file.
- **GET /health** – Returns `{"status": "ok"}`.
