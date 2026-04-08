## medipilot-ai

Production-ready starter for a **Browser Agent Process Automation** system for Healthcare EHR using:

- **BentoML** (AI services)
- **Playwright** (browser automation)
- **LangGraph-ready** workflow boundaries
- **OpenAI** for LLM (auto-mocks when `OPENAI_API_KEY` is not set)

Python **3.12**.

## What’s included (current features)

- **Backend AI services (BentoML)**:
  - `POST /run_full_workflow`: clinical extraction → coding suggestions → validation
  - `POST /health`: health check + UTC timestamp
  - **Deterministic mock mode** when `OPENAI_API_KEY` is missing (runs end-to-end without external calls)
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

```bash
curl -X POST http://localhost:3000/run_full_workflow ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"45M presents with fever and cough...\",\"request_id\":\"00000000-0000-0000-0000-000000000000\"}"
```

## Notes

- If `OPENAI_API_KEY` is empty, the backend returns deterministic mock JSON so the system runs end-to-end.
- Update `data/mock_ehr_pages.html` to mirror the real EHR page structure you plan to automate.

