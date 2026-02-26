"""
HTTP API for RAG: /query, /ingest/url, /ingest/document (PDF/DOCX), /health.
"""
import os
import traceback
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import KNOWLEDGE_PATH, URL_CONTENT_PATH
from rag_core import query_rag
from ingest import (
    ingest_pdf,
    ingest_docx,
    ingest_url,
    ingest_knowledge_file,
    reingest_all_sources,
    parse_url_content_file,
    remove_url_from_knowledge_base,
    update_url_content,
    list_documents,
    get_document_content,
    save_document,
    delete_document,
    parse_qna_file,
    append_qna,
    delete_all_qna,
    delete_qna_at_index,
)

app = FastAPI(title="RAG API", description="Query and ingest into the knowledge base")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]


class IngestUrlRequest(BaseModel):
    url: str


class IngestResponse(BaseModel):
    ok: bool
    message: str
    chunks_added: int | None = None


class KnowledgeContent(BaseModel):
    content: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    try:
        result = query_rag(request.question)
        return QueryResponse(answer=result["answer"], sources=result.get("sources", []))
    except ValueError as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge")
def get_knowledge():
    """Return the current knowledge base file content."""
    path = Path(KNOWLEDGE_PATH)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    if not path.exists():
        return {"content": ""}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return {"content": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/knowledge")
def save_knowledge(body: KnowledgeContent):
    """Save content to knowledge base file and re-ingest into Chroma (replaces existing KB)."""
    path = Path(KNOWLEDGE_PATH)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body.content or "", encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    try:
        n = reingest_all_sources()
        return IngestResponse(ok=True, message="Knowledge base saved and updated.", chunks_added=n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/url", response_model=IngestResponse)
def ingest_url_endpoint(body: IngestUrlRequest):
    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    try:
        n = ingest_url(url)
        return IngestResponse(ok=True, message=f"Ingested URL: {url}", chunks_added=n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/document", response_model=IngestResponse)
async def ingest_document_endpoint(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    content = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    try:
        if suffix == ".pdf":
            n = ingest_pdf(content, filename=file.filename)
        elif suffix == ".docx":
            n = ingest_docx(content, filename=file.filename)
        else:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX are supported")
        return IngestResponse(ok=True, message=f"Ingested: {file.filename}", chunks_added=n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Sources / URLs / Documents / Q&A ---

@app.get("/sources")
def get_sources():
    """List all sources: URLs, documents, Q&A."""
    urls = parse_url_content_file()
    docs = list_documents()
    qna = parse_qna_file()
    return {"urls": urls, "documents": docs, "qna": qna}


@app.get("/urls")
def get_urls():
    """List all URLs with their extracted content."""
    return {"urls": parse_url_content_file()}


@app.delete("/urls")
def delete_url(url: str):
    """Remove a URL from the knowledge base (Chroma + url_content.txt)."""
    url = (url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url query param required")
    remove_url_from_knowledge_base(url)
    return {"ok": True, "message": f"Removed URL: {url}"}


class UpdateUrlBody(BaseModel):
    url: str
    content: str


@app.put("/urls")
def put_url(body: UpdateUrlBody):
    """Update stored content for a URL and re-ingest."""
    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    update_url_content(url, body.content or "")
    return {"ok": True, "message": f"Updated URL: {url}"}


@app.get("/documents")
def get_documents_list():
    """List all named text documents."""
    return {"documents": list_documents()}


@app.get("/documents/{doc_id}")
def get_document(doc_id: str):
    """Get content of a document."""
    content = get_document_content(doc_id)
    return {"id": doc_id, "content": content}


class DocumentBody(BaseModel):
    name: str
    content: str


@app.post("/documents")
def create_document(body: DocumentBody):
    """Create a new text document (id derived from name)."""
    import re
    doc_id = re.sub(r"[^\w\-]", "_", (body.name or "doc").strip())[:50] or "doc"
    n = save_document(doc_id, body.name or doc_id, body.content or "")
    return IngestResponse(ok=True, message=f"Document created: {body.name}", chunks_added=n)


@app.put("/documents/{doc_id}")
def update_document(doc_id: str, body: DocumentBody):
    """Update document content and re-ingest."""
    n = save_document(doc_id, body.name or doc_id, body.content or "")
    return IngestResponse(ok=True, message="Document updated.", chunks_added=n)


@app.delete("/documents/{doc_id}")
def delete_document_endpoint(doc_id: str):
    """Delete a document and its chunks."""
    delete_document(doc_id)
    return {"ok": True, "message": f"Deleted document: {doc_id}"}


@app.get("/qna")
def get_qna():
    """List all Q&A pairs."""
    return {"qna": parse_qna_file()}


class QnaBody(BaseModel):
    question: str
    answer: str


@app.post("/qna")
def add_qna(body: QnaBody):
    """Add a Q&A pair to the knowledge base."""
    n = append_qna(body.question or "", body.answer or "")
    return IngestResponse(ok=True, message="Q&A added.", chunks_added=n)


@app.delete("/qna")
def delete_qna_all():
    """Remove all Q&A from the knowledge base."""
    delete_all_qna()
    return {"ok": True, "message": "All Q&A removed."}


@app.delete("/qna/{index}")
def delete_qna_one(index: int):
    """Remove the Q&A pair at index (0-based)."""
    try:
        delete_qna_at_index(index)
        return {"ok": True, "message": f"Q&A at index {index} removed."}
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Serve chat UI from / (if static folder exists)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(static_dir, "index.html"))


def run():
    import uvicorn
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT") or os.environ.get("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
