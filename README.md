## medipilot-ai

Production-ready starter for a **Browser Agent Process Automation** system for Healthcare EHR using:

- **BentoML** (AI services)
- **Playwright** (browser automation)
- **LangGraph-ready** workflow boundaries
- **OpenAI** for LLM (auto-mocks when `OPENAI_API_KEY` is not set)

Python **3.12**.

## What’s included (current features)

- **Backend AI services (BentoML)**:
  - `POST /run_full_workflow`: LangGraph workflow — clinical extraction → coding suggestions → validation
  - `POST /health`: health check + UTC timestamp
  - **Clinical vector memory** (`backend/utils/memory.py`): in-process Qdrant stores embedded cases; retrieval returns up to **3** past cases sorted by similarity, only if cosine score is **strictly greater than 0.7**; otherwise retrieval is empty and the server logs `No relevant memory found` (configure logging at INFO to see it).
  - **Clinical prompt** (`backend/prompts/clinical_prompt.txt`): **Patient data**, **Relevant past cases** (plain-text summaries, not raw JSON), and **Instructions** so the model prioritizes the current note and does not blindly copy prior diagnoses.
  - **Workflow response** includes **`memory_used`**: `true` when at least one retrieved case was injected into the prompt, `false` otherwise.
  - **`POST /extract_clinical_data`** (when serving the clinical service): same extraction path; response merges clinical fields with **`memory_used`**.
  - **Deterministic mock mode** when `OPENAI_API_KEY` is missing (runs end-to-end without external calls; embeddings use a deterministic hash-based mock)
  - **Request correlation**: `request_id` accepted + returned for tracing across backend + agent logs
- **Browser agent (Playwright)**:
  - Opens local `data/mock_ehr_pages.html` (mock EHR)
  - Extracts visible page text and sends to backend workflow
  - Prints structured JSON result and **fills mock form fields** (`#icd_codes`, `#cpt_codes`, `#confidence`)
  - **Resilient backend calls** with retries + exponential backoff
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

```bash
bentoml serve backend.main:svc --host 0.0.0.0 --port 3000
```

Optional: verify the backend is up:

```bash
curl http://localhost:3000/health
```

### 4) Install Playwright (for browser agent)

```bash
pip install playwright requests
playwright install chromium
```

### 5) Run browser agent

```bash
python "browser-agent/main.py"
```

You should see the structured workflow result printed, and the mock EHR fields get filled.

## Run with Docker Compose

From the repo root:

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Example API calls

### Run full workflow

Response includes `request_id`, `clinical`, `coding`, `validation`, and **`memory_used`** (`true` | `false`).

```bash
curl -X POST http://localhost:3000/run_full_workflow ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"45M presents with fever and cough...\",\"request_id\":\"00000000-0000-0000-0000-000000000000\"}"
```

## Notes

- If `OPENAI_API_KEY` is empty, the backend returns deterministic mock JSON so the system runs end-to-end.
- Vector memory uses an **in-memory** Qdrant instance: it does not persist across process restarts. Tuning: `MIN_SIMILARITY_SCORE` and related helpers in `backend/utils/memory.py`.
- Update `data/mock_ehr_pages.html` to mirror the real EHR page structure you plan to automate.

