# Step-by-Step: Deploy RAG App on Railway (Free Plan)

Follow these steps in order. You need: a GitHub account, a Railway account, and your API keys (GEMINI_API_KEY, GROQ_API_KEY).

---

## Step 1: Put your code on GitHub (Windows + Git)

1. **Create a new repo on GitHub**  
   Go to [github.com/new](https://github.com/new), name it (e.g. `my-rag-app`). Do **not** add a README, .gitignore, or license (you already have local code).

2. **Open PowerShell** in your project folder:
   ```powershell
   cd C:\Users\admin\Downloads\codefile
   ```

3. **Initialize git** (if this folder is not already a repo):
   ```powershell
   git init
   ```

4. **Add the `.gitignore`**  
   The project already has a `.gitignore` that ignores `chroma_db/`, `.env`, `documents/`, `url_content.txt`, `qna.txt`, and Python cache. `knowledge.txt` is **not** ignored, so it will be committed as initial content.

5. **Stage and commit:**
   ```powershell
   git add .
   git status
   git commit -m "Initial commit for Railway deploy"
   ```

6. **Add the GitHub repo and push** (replace `YOUR_USERNAME` and `my-rag-app` with your GitHub username and repo name):
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/my-rag-app.git
   git branch -M main
   git push -u origin main
   ```
   If GitHub asks for login, use a **Personal Access Token** as the password (GitHub → Settings → Developer settings → Personal access tokens).

---

## Step 2: Create a Railway project and deploy from GitHub

1. Go to [railway.app](https://railway.app) and sign in (e.g. with GitHub).
2. Click **“New Project”**.
3. Choose **“Deploy from GitHub repo”** and select the repo you pushed (e.g. `my-rag-app`).
4. Railway will detect Python and build from `requirements.txt`. Wait for the first build to finish (it may fail until we set env vars and add a volume; that’s OK).

---

## Step 3: Add a Volume (persistent storage)

Without a volume, Chroma and all knowledge files are lost on every restart.

1. In the Railway dashboard, open your **service** (the app you just created).
2. Go to the **“Variables”** or **“Settings”** tab and find **“Volumes”** (or **“Storage”**).
3. Click **“Add Volume”** or **“Attach Volume”**.
4. Set the **mount path** to: `/data`
5. Create/save the volume. Railway will give you 0.5 GB on the free plan.

---

## Step 4: Set environment variables

In the same service, go to **“Variables”** and add these. Replace placeholder values with your real keys and paths.

| Variable | Value |
|----------|--------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `GROQ_API_KEY` | Your Groq API key |
| `CHROMA_PATH` | `/data/chroma_db` |
| `KNOWLEDGE_PATH` | `/data/knowledge.txt` |
| `URL_CONTENT_PATH` | `/data/url_content.txt` |
| `QNA_PATH` | `/data/qna.txt` |
| `DOCUMENTS_DIR` | `/data/documents` |

- **PORT** is set by Railway; you do **not** need to add it.
- Do **not** commit `.env` or real keys to GitHub.

---

## Step 5: Set the start command (if needed)

Railway usually detects a **Procfile**. If your app does not start:

1. In the service, go to **Settings**.
2. Find **“Build”** or **“Deploy”** and set **Start Command** to:
   ```bash
   uvicorn api:app --host 0.0.0.0 --port $PORT
   ```
   Or leave it empty if the Procfile (`web: uvicorn api:app --host 0.0.0.0 --port $PORT`) is already used.

---

## Step 6: Redeploy and get a public URL

1. Trigger a new deploy (e.g. **“Redeploy”** or push a new commit to `main`).
2. In the service, open the **“Settings”** or **“Networking”** tab.
3. Click **“Generate Domain”** (or “Add Public URL”). Railway will give you a URL like `https://your-app-name.up.railway.app`.
4. Open that URL in a browser. You should see your RAG chat UI.

---

## Step 7: Point the UI at the deployed API

The chat page has an **“API”** input. Set it to your Railway URL, e.g.:

- `https://your-app-name.up.railway.app`

Then use **Chat** and **Knowledge base** as usual.

---

## Step 8: Add knowledge after first deploy

On first deploy, the volume is empty (no `knowledge.txt`, no Chroma data). So:

1. Open your Railway URL.
2. Go to **Knowledge base → Main text**, type or paste content, and click **Save**.
3. Or add URLs (**Add URL**), documents, or Q&A as needed.

All of this is stored on the volume at `/data`, so it persists across redeploys.

---

## Summary checklist

| Step | Action |
|------|--------|
| 1 | Push code to GitHub (with `.gitignore` for secrets and optional `*.txt`). |
| 2 | New Railway project → Deploy from GitHub repo. |
| 3 | Add Volume, mount path `/data`. |
| 4 | Set env vars: `GEMINI_API_KEY`, `GROQ_API_KEY`, `CHROMA_PATH`, `KNOWLEDGE_PATH`, `URL_CONTENT_PATH`, `QNA_PATH`, `DOCUMENTS_DIR` (all `/data/...`). |
| 5 | Start command: `uvicorn api:app --host 0.0.0.0 --port $PORT` (or use Procfile). |
| 6 | Generate domain and open the URL. |
| 7 | Set “API” in the UI to that URL. |
| 8 | Add knowledge (main text, URLs, docs, Q&A) via the UI. |

---

## If something goes wrong

- **Build fails:** Check the build logs. Ensure `requirements.txt` and `runtime.txt` (if used) are in the repo and that Python version is supported.
- **App crashes or “Application failed”:** Check deploy/runtime logs. Often missing env vars (e.g. `GEMINI_API_KEY`) or wrong start command.
- **Knowledge disappears after redeploy:** Volume not attached or env vars not set to `/data/...`. Re-do Step 3 and Step 4.
- **502 / timeout:** Free tier may sleep when idle; first request can be slow. Wait and try again.
