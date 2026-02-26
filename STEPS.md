# Steps to Run and Deploy Your RAG System

Follow these in order. Steps 1–5 get you running locally; Step 6 is optional AWS deployment.

---

## Step 1: Install dependencies

```bash
pip install -r requirements.txt
```

You need: Python 3.10+.

---

## Step 2: Set API keys

Set these in your environment (do not commit them).

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY = "your-gemini-api-key"
$env:GROQ_API_KEY = "your-groq-api-key"
```

**Linux / macOS:**
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export GROQ_API_KEY="your-groq-api-key"
```

- Gemini: [Google AI Studio](https://aistudio.google.com/apikey) (embeddings).
- Groq: [console.groq.com](https://console.groq.com/) (generation).

---

## Step 3: Ingest content into the knowledge base

The RAG uses a **vector store (Chroma)**. You must ingest at least one source before querying.

**Option A – Ingest the sample `knowledge.txt`:**
```bash
python -c "from ingest import ingest_knowledge_file; n=ingest_knowledge_file(); print(f'Added {n} chunks')"
```

**Option B – Ingest a URL:**
```bash
curl -X POST http://localhost:8000/ingest/url -H "Content-Type: application/json" -d "{\"url\": \"https://example.com/page\"}"
```
(Start the API first; see Step 4.)

**Option C – Ingest a PDF or DOCX via API:**

Start the API (Step 4), then:

```bash
curl -X POST http://localhost:8000/ingest/document -F "file=@/path/to/document.pdf"
```

Or use the API docs at `http://localhost:8000/docs` to upload a file.

**Chroma data** is stored in the `chroma_db/` folder in the project directory. You can delete that folder to start with an empty knowledge base.

---

## Step 4: Start the API (and chat UI)

From the project directory:

```bash
python api.py
```

Or:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

- **API:** http://localhost:8000  
- **Chat UI:** http://localhost:8000/ (served by the same process)  
- **OpenAPI docs:** http://localhost:8000/docs  

In the chat page, type a question and click **Ask**. The API uses the ingested knowledge base to answer.

---

## Step 5: Optional – CLI instead of website

If you prefer a terminal:

```bash
python rag.py
```

Make sure you have ingested something (Step 3) first. The CLI uses the same Chroma store and keys.

---

## Step 6: Deploy to AWS (Free Tier friendly)

These steps get the RAG running on AWS in a way that fits Free Tier and can scale later.

### 6.1 What you need on AWS

- **EC2** (e.g. t2.micro or t3.micro) – 750 hrs/month free for 12 months.
- **RDS** is optional; you can keep using **Chroma on the same EC2** (data in `chroma_db/` on the instance or on an EBS volume). For larger scale later, switch to **pgvector on RDS**.
- **S3** (optional) – store uploaded PDFs/DOCX; 5 GB free tier.

### 6.2 Prepare the project

1. **Freeze dependencies:**
   ```bash
   pip freeze > requirements-freeze.txt
   ```
   Use `requirements-freeze.txt` on the server if you want exact versions.

2. **Environment variables:** Do not put keys in code. On EC2, set them in the OS or use AWS Systems Manager Parameter Store (or Secrets Manager):
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - Optionally `CHROMA_PATH` (e.g. `/var/rag/chroma_db`)

### 6.3 Launch EC2 and run the API

1. Launch an **Amazon Linux 2** or **Ubuntu** instance (t2.micro).
2. Install Python 3.10+, git, and create a user for the app.
3. Clone/copy your project onto the instance.
4. Create a virtualenv, install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
5. Set env vars (e.g. in `~/.bashrc` or a small `.env` file loaded by your process manager).
6. Run the API so it keeps running:
   - **Simple:** `nohup uvicorn api:app --host 0.0.0.0 --port 8000 &`
   - **Better:** use **systemd** or **supervisor** to run `uvicorn api:app --host 0.0.0.0 --port 8000`.
7. Open **port 8000** in the instance **Security Group** (inbound rule for HTTP or your chosen port).

### 6.4 Point the website to the API

- If the chat UI is served by the same API (as in this project), open `http://<EC2-public-IP>:8000/` in a browser.
- For a **custom domain** and HTTPS later: put a reverse proxy (e.g. **Nginx** or **Caddy**) in front of the app and use **Let’s Encrypt**, or put the app behind **Application Load Balancer** and use **ACM** for SSL.

### 6.5 Optional: S3 for uploads

- Create an S3 bucket for uploaded PDFs/DOCX.
- In your app you can later add: “Upload file to S3 → trigger ingestion” (e.g. Lambda or a worker on EC2 that reads from S3 and runs your ingest code). For the current code, ingestion is done via the API (`/ingest/document` and `/ingest/url`); you can keep that and optionally store the file in S3 in the same request.

### 6.6 Long-term scalability

- **More traffic:** Increase EC2 size or add more instances behind a load balancer; keep Chroma on a shared EBS or migrate to **pgvector on RDS** (or a dedicated vector DB).
- **Larger knowledge base:** Use **pgvector** (PostgreSQL extension) on RDS instead of Chroma; change `rag_core` to query PostgreSQL. Same ingestion flow; only the “store/query vectors” part changes.
- **Multi-tenant:** Add a `tenant_id` (or `company_id`) to your chunks and filter every query by it so each business only sees its own data.

---

## Quick reference

| Task | Command or URL |
|------|-----------------|
| Install deps | `pip install -r requirements.txt` |
| Ingest `knowledge.txt` | `python -c "from ingest import ingest_knowledge_file; ingest_knowledge_file()"` |
| Start API + UI | `python api.py` or `uvicorn api:app --host 0.0.0.0 --port 8000` |
| Chat in browser | http://localhost:8000/ |
| API docs | http://localhost:8000/docs |
| Query (curl) | `curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d "{\"question\": \"...\"}"` |
| Ingest URL | `POST /ingest/url` with `{"url": "https://..."}` |
| Ingest PDF/DOCX | `POST /ingest/document` with multipart file |
| CLI chat | `python rag.py` |
