## medipilot-ai

Production-ready starter for a **Browser Agent Process Automation** system for Healthcare EHR using:

- **BentoML** (AI services)
- **Playwright** (browser automation)
- **Next.js** (optional UI to run the workflow and trigger automation)
- **LangGraph-ready** workflow boundaries
- **OpenAI** for LLM (auto-mocks when `OPENAI_API_KEY` is not set)

Python **3.12**.

## What’s included (current features)

- **Backend AI services (BentoML)**:
  - `POST /run_full_workflow`: LangGraph workflow — clinical extraction → coding suggestions → validation
  - `POST /run_browser_automation`: runs Playwright to open the mock EHR, fill diagnosis/ICD from the last workflow result, and submit (used by the **Approve** action in the frontend)
  - `POST /get_screenshot`: returns the latest automation screenshot as base64 JSON: `{ "image": "<base64>" }` (frontend renders via a `data:` URL; avoids direct image hotlinking)
  - `POST /health`: health check (`status`, `service`)
  - **CORS** enabled for `http://localhost:3000` (Next.js dev origin) in `backend/main.py`
  - **Clinical vector memory** (`backend/utils/memory.py`): in-process Qdrant stores embedded cases; retrieval returns up to **3** past cases sorted by similarity, only if cosine score is **strictly greater than 0.7**; otherwise retrieval is empty and the server logs `No relevant memory found` (configure logging at INFO to see it).
  - **Clinical prompt** (`backend/prompts/clinical_prompt.txt`): **Patient data**, **Relevant past cases** (plain-text summaries, not raw JSON), and **Instructions** so the model prioritizes the current note and does not blindly copy prior diagnoses.
  - **Workflow response** includes **`memory_used`**: `true` when at least one retrieved case was injected into the prompt, `false` otherwise.
  - **`POST /extract_clinical_data`** (when serving the clinical service): same extraction path; response merges clinical fields with **`memory_used`**.
  - **Deterministic mock mode** when `OPENAI_API_KEY` is missing (runs end-to-end without external calls; embeddings use a deterministic hash-based mock)
  - **Request correlation**: `request_id` accepted + returned for tracing across backend + agent logs
- **Frontend (`frontend/`)**:
  - **MediPilot AI** page: paste clinical text, **Run AI** → calls `POST /run_full_workflow`, shows clinical/coding/validation-style fields
  - **Approve** → `POST /run_browser_automation` with `clinical` + `coding` from the result (expects API on **`http://localhost:3001`** in the current build), then `POST /get_screenshot` and renders `data:image/png;base64,...`
- **Browser agent (`browser_agent/`, Playwright)**:
  - **CLI path** (`python browser_agent/main.py`): opens `data/mock_ehr_pages.html` via `file://`, runs observe → think → act, calls backend `POST /run_full_workflow`, fills labeled fields, submits
  - **API path** (`run_browser_automation`): opens **`http://localhost:8000/mock-ehr.html`** — run a static server from `browser_agent/` (e.g. `python -m http.server 8000`) so that URL serves `mock-ehr.html`
  - **Windows + BentoML**: Playwright runs with **`WindowsProactorEventLoopPolicy`** when needed so subprocess-based driver startup works inside BentoML’s worker threads
  - **Resilient backend calls** (CLI client) with retries + exponential backoff
- **Docker Compose demo**:
  - Builds and runs backend + browser-agent containers
  - Backend includes a `/health` healthcheck; browser-agent waits for backend readiness

## Docs

- **Project overview & complete feature list**: `PROJECTOVERVIEW.md`
- **Architecture**: `docs/architecture.md`
- **Workflow details**: `docs/workflows.md`
- **API spec**: `docs/api-spec.md`

## Quickstart (local)

### 1) Create/activate venv

```bash
python -m venv .venv
```

### 2) Install backend deps

```bash
pip install -r backend/requirements.txt
```

### 3) Run backend (BentoML)

Default port in docs and Docker is **3000**. The **Next.js app** in this repo calls the API on **3001**, so for the full UI flow use:

```bash
bentoml serve backend.main:svc --host 0.0.0.0 --port 3001
```

Optional: verify the backend is up:

```bash
curl http://localhost:3001/health
```

(Use port **3000** if you are not using the bundled frontend or you change the frontend URLs.)

### 4) Install Playwright (for browser agent)

```bash
pip install playwright requests
playwright install chromium
```

### 5) Mock EHR over HTTP (for `/run_browser_automation`)

From the repo root:

```bash
cd browser_agent
python -m http.server 8000
```

Leave this running while testing **Approve** / `POST /run_browser_automation`.

### 6) Run browser agent (CLI demo)

From the repo root (ensure `PYTHONPATH` includes the repo root, or run from an environment where `browser_agent` resolves):

```bash
python browser_agent/main.py
```

You should see the structured workflow result printed and the mock EHR (file-based) fields filled.

### 7) Run frontend (optional)

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (usually `http://localhost:3000`). Use **Run AI**, then **Approve** to trigger browser automation (backend on **3001**, mock EHR server on **8000**).

## Run with Docker Compose

From the repo root:

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Example API calls

### Run full workflow

Response includes `request_id`, `clinical`, `coding`, `validation`, and **`memory_used`** (`true` | `false`).

```bash
curl -X POST http://localhost:3001/run_full_workflow ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"45M presents with fever and cough...\",\"request_id\":\"00000000-0000-0000-0000-000000000000\"}"
```

### Run browser automation

Body must include `clinical` and `coding` objects (as returned by `run_full_workflow`).

```bash
curl -X POST http://localhost:3001/run_browser_automation ^
  -H "Content-Type: application/json" ^
  -d "{\"clinical\":{\"diagnosis\":[\"Example\"]},\"coding\":{\"icd_codes\":[\"A00.0\"]}}"
```

### Get latest automation screenshot (base64)

`/get_screenshot` returns JSON with an `image` field containing base64-encoded PNG bytes.

```bash
curl -X POST http://localhost:3001/get_screenshot
```

## Notes

- If `OPENAI_API_KEY` is empty, the backend returns deterministic mock JSON so the system runs end-to-end.
- Vector memory uses an **in-memory** Qdrant instance: it does not persist across process restarts. Tuning: `MIN_SIMILARITY_SCORE` and related helpers in `backend/utils/memory.py`.
- **`data/mock_ehr_pages.html`** is used by the **CLI** agent (`file://`). **`browser_agent/mock-ehr.html`** is used by **`/run_browser_automation`** over **HTTP** on port 8000. Keep them in sync if you change field names or layout.
- If you change API port or frontend origin, update **`frontend/src/app/page.tsx`** fetch URLs and **`backend/main.py`** `CORSMiddleware` `allow_origins` accordingly.

## Author

**Jayendran Subramanian (Full Stack Data Engineer & AI Builder)**  
- Passionate about Agentic AI, Data Engineering, and AI-driven automation  
- Building real-world AI systems for healthcare and enterprise use cases  

🔗 LinkedIn: [linkedin.com/in/csjayendran](https://www.linkedin.com/in/csjayendran/)
🔗 GitHub: [https://github.com/YOUR-USERNAME](https://github.com/js731981)

## Disclaimer

MediPilot AI is an MVP (Minimum Viable Product) designed to demonstrate agentic AI capabilities in healthcare workflow automation.
- This system is not a medical device and is not approved for clinical use.
- It does NOT provide medical advice, diagnosis, or treatment.
- All outputs are AI-generated and should be considered experimental.
- Any deployment involving real patient data requires compliance with healthcare regulations (e.g., HIPAA, GDPR) and proper clinical validation.
Use of this system in real-world healthcare settings must include qualified human oversight and regulatory approval.
The author disclaims any liability for misuse or unintended use of this system.


