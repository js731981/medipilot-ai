## Project Overview — medipilot-ai

`medipilot-ai` is a working, end-to-end starter for **EHR browser automation powered by an AI workflow**. It is intentionally “thin but complete”: a BentoML backend that turns clinical text into structured extraction + coding suggestions, optional **Next.js** UI to review results and trigger automation, and a **Playwright** browser agent that drives mock EHR pages.

This repo is set up so you can:

- Run locally with deterministic mocks (no API keys required)
- Swap in real LLM calls by adding `OPENAI_API_KEY`
- Use a **LangGraph**-compiled workflow for the default `run_full_workflow` path (with optional similar-case retrieval from in-memory vector memory)
- Trigger **headful** Playwright runs from the API (`/run_browser_automation`) or run the **CLI** agent loop end-to-end

## Current feature set (complete)

### Backend (BentoML service)

- **Workflow API (default service, `backend/services/workflow_service.py`)**:
  - **`POST /run_full_workflow`**: runs a sequential workflow:
    - Clinical extraction
    - Coding suggestions
    - Output validation
  - **`POST /run_browser_automation`**: imports `browser_agent.main.run_browser_automation`, runs Playwright **synchronously** (Chromium, headful in current code), navigates to **`http://localhost:8000/mock-ehr.html`**, fills `diagnosis` / `icd` inputs from the payload, submits the form. Intended payload shape: `{ "clinical": {...}, "coding": {...} }` as produced by `run_full_workflow`.
  - **Input** (`run_full_workflow`): `{ "text": string, "request_id"?: uuid-string }`
  - **Output** (`run_full_workflow`): `{ "request_id": uuid-string, "clinical": {...}, "coding": {...}, "validation": {...}, "memory_used": boolean }`
    - **`memory_used`**: `true` when the clinical step injected non-empty similar-case text into the LLM prompt (see **Clinical vector memory** below); `false` when no case met the similarity threshold or retrieval failed.
  - **Output** (`run_browser_automation`): `{ "status": "success", "message": "Automation completed" }` on success.
- **Health endpoint**:
  - **`POST /health`** returns `{ "status": "ok", "service": "medipilot-ai" }` for readiness/liveness checks
- **ASGI middleware** (`backend/main.py`):
  - **CORS** with `allow_origins=["http://localhost:3000"]` so the Next.js dev app can call a backend on another port (e.g. **3001**).
- **Deterministic mock mode** (no external dependency):
  - If `OPENAI_API_KEY` is not set, the backend returns deterministic JSON compatible with the prompts, so the system runs end-to-end without network calls.
- **Typed schemas & validation**:
  - Pydantic schemas for `ClinicalEntities`, `CodingSuggestion`, and `WorkflowResult`
  - Validation agent checks required keys/types and confidence range \(0.0..1.0\)
- **Prompt-driven agents**:
  - Prompt templates live under `backend/prompts/`
  - Agents are pure functions under `backend/agents/`
- **Clinical vector memory** (`backend/utils/memory.py`):
  - **Qdrant** client over **`:memory:`** (no disk persistence; resets when the process exits).
  - **`store_case`**: embeds clinical note text (OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` is set, otherwise a deterministic mock embedding), stores diagnosis, optional codes, confidence, timestamp.
  - **`search_similar_cases`**: cosine similarity search; results sorted by score (descending); **at most 3** cases returned; default gate **`score > MIN_SIMILARITY_SCORE` (0.7)** — callers may override via `min_score`.
  - **`retrieve_similar_cases_text`**: returns a **plain-text** block for prompts (not JSON), e.g. labeled lines for symptoms (from stored text), diagnosis, confidence, and date.
  - When no point passes the threshold after search, the module logs **`No relevant memory found`** at INFO (ensure your logging config shows `backend.utils.memory`).
- **Clinical extraction prompt** (`clinical_prompt.txt`):
  - Sections: **Patient data** (current note), **Relevant past cases** (from memory or empty), **Instructions** (use past cases only if relevant; do not blindly copy diagnosis; prioritize current patient data), plus explicit reasoning guidance to reduce retrieval bias.
- **Request correlation (`request_id`)**:
  - `request_id` is accepted, normalized, and returned in `run_full_workflow` responses
  - Used for end-to-end log correlation across backend and browser agent

### Frontend (`frontend/`)

- **Next.js 16** + React 19 + Tailwind (see `frontend/package.json`).
- **Home page** (`frontend/src/app/page.tsx`):
  - Text area for clinical note, **Run AI** → `POST http://localhost:3001/run_full_workflow`
  - Renders symptoms, diagnosis, procedures, ICD/CPT, confidence from the response
  - **Approve** → `POST http://localhost:3001/run_browser_automation` with `{ clinical, coding }` from the last result
  - **Reject** is a placeholder (alert only)
- **Typical local ports**: Next dev **3000**, BentoML **3001**, static mock EHR **8000** (see README quickstart).

### Workflow implementation

- **Agent boundaries** (unchanged contracts for coding/validation inputs):
  - `extract_clinical_entities(text) -> tuple[clinical_dict, memory_used_bool]`
  - `suggest_medical_codes(clinical)` — receives only entity fields (no `memory_used` on this dict)
  - `validate_output({clinical, coding})`
- **Default full workflow (LangGraph)**:
  - Implemented in `backend/workflows/langgraph_workflow.py`: `START → clinical → coding → validation → END`
  - State carries **`memory_used`** alongside `clinical`, `coding`, and `validation`.
- **Alternate sequential graph**:
  - `backend/workflows/clinical_workflow.py` exposes a similar linear graph with the same agent functions and **`memory_used`** in state (useful for tests or alternate wiring).

### Browser agent (`browser_agent/`, Playwright)

- **Package layout**: Python package under `browser_agent/` (underscore). Imports use `browser_agent.main` from the backend.
- **Two mock EHR entry paths**:
  1. **CLI / patient flow** (`python browser_agent/main.py` → `run_patient_flow`): opens **`data/mock_ehr_pages.html`** via **`file://`** (`navigation/ehr_navigation.open_mock_ehr`).
  2. **API-driven automation** (`run_browser_automation`): opens **`http://localhost:8000/mock-ehr.html`** (serve `browser_agent/` with e.g. `python -m http.server 8000`).
- **Agent loop (CLI)** — observe → think → act:
  - **Observe**: extracts visible text from the page
  - **Think**: calls backend `POST /run_full_workflow`
  - **Act**: fills labeled inputs / clicks as implemented in `workflows/patient_flow.py` and `actions/`
- **Windows + BentoML thread pool**:
  - Before `sync_playwright()`, **`run_browser_automation`** sets **`asyncio.WindowsProactorEventLoopPolicy()`** on Windows so Playwright can spawn the driver subprocess from a BentoML worker thread (avoids `NotImplementedError` on subprocess transports).
- **Resilience**:
  - Backend HTTP client used by the agent includes retries for connection/timeout errors with exponential backoff where implemented.
- **Runtime controls**:
  - `HEADLESS=true|false` for the **CLI** path (`launch_browser`)
  - `BACKEND_URL` to target local backend or Docker Compose backend service

### Docker Compose (infra demo)

- **Two services**:
  - `backend`: BentoML service exposed on host port `3000`
  - `browser-agent`: Playwright runner that waits for backend health before starting
- **Healthcheck-gated startup**:
  - Compose healthcheck calls `/health` and only starts browser-agent when backend is healthy.

## Repository map (what lives where)

- **Backend**: `backend/`
  - Service entry: `backend/main.py` (exports `svc` → workflow service by default; CORS + optional other service imports)
  - Workflow service: `backend/services/workflow_service.py` (`run_full_workflow`, `run_browser_automation`, `health`)
  - Workflow logic: **`backend/workflows/langgraph_workflow.py`** (default path for `run_full_workflow`)
  - Alternate workflow: `backend/workflows/clinical_workflow.py`
  - Agents: `backend/agents/` (e.g. `clinical_agent.py`, `coding_agent.py`, `validation_agent.py`)
  - Vector memory utilities: `backend/utils/memory.py`
  - Prompts: `backend/prompts/`
  - Schemas: `backend/schemas/`
  - Settings: `backend/config/settings.py`
- **Frontend**: `frontend/` (Next.js app, `src/app/page.tsx`)
- **Browser agent**: `browser_agent/`
  - Entry: `browser_agent/main.py` (`main()` CLI, `run_browser_automation()` for API)
  - Agent loop: `browser_agent/core/agent_loop.py`
  - Workflow wrapper: `browser_agent/workflows/patient_flow.py`
  - Backend client: `browser_agent/client/bento_client.py`
  - Navigation: `browser_agent/navigation/ehr_navigation.py`
  - Mock page (HTTP): `browser_agent/mock-ehr.html`
- **Mock EHR page (file / CLI)**: `data/mock_ehr_pages.html`
- **Docker/compose**: `infra/docker-compose.yml`, `infra/docker/*.Dockerfile`
- **Additional docs**: `docs/`

## APIs (quick reference)

- **Backend base URL**: `http://localhost:3000` in Docker/README defaults; **`http://localhost:3001`** matches the current frontend fetch URLs.
- **`POST /run_full_workflow`**:
  - Request: `{ "text": "..." }` (optionally include `request_id`)
  - Response:
    - `clinical`: `{ symptoms: string[], diagnosis: string[], procedures: string[], confidence: number }`
    - `coding`: `{ icd_codes: string[], cpt_codes: string[], confidence: number }`
    - `validation`: `{ valid: boolean, issues: string[] }`
    - **`memory_used`**: boolean — whether similar-case text was included in the clinical LLM prompt
    - `request_id`: `uuid-string`
- **`POST /run_browser_automation`**:
  - Request: `{ "clinical": { ... }, "coding": { ... } }` (typically the objects returned by `run_full_workflow`)
  - Response: `{ "status": "success", "message": "Automation completed" }`
  - Requires a server at **`http://localhost:8000`** serving **`mock-ehr.html`** (see README).
- **`POST /extract_clinical_data`** (when the clinical Bento service is mounted):
  - Response merges the clinical entity object with **`memory_used`** in one JSON object.
- **`POST /health`**:
  - Response: `{ "status": "ok", "service": "medipilot-ai" }`

For the formal spec, see `docs/api-spec.md` (update that file if you add routes or change contracts).

## Configuration

- **`OPENAI_API_KEY`**:
  - Not set → deterministic mock responses
  - Set → real OpenAI calls via the `openai` SDK
- **`OPENAI_MODEL`**:
  - Defaults to `gpt-4o-mini` if not set
- **`OPENAI_EMBEDDING_MODEL`** (optional):
  - Used for vector memory when `OPENAI_API_KEY` is set; defaults to `text-embedding-3-small` (must match embedding size configured in `memory.py`)
- **`BACKEND_URL`** (browser agent CLI client):
  - Defaults to `http://localhost:3000`
  - In Docker Compose: `http://backend:3000`
- **`HEADLESS`** (browser agent CLI):
  - Default: `true` (set `false` to see the browser)

## Extension points (where to add new capabilities)

- **Add more EHR actions**: `browser_agent/actions/` and `browser_agent/navigation/`
- **Improve extraction/coding prompts**: `backend/prompts/`
- **Add new agent steps**:
  - Implement in `backend/agents/`
  - Wire into `backend/workflows/langgraph_workflow.py` (and/or `clinical_workflow.py` if you keep that graph in sync)
- **Tune retrieval**:
  - Adjust `MIN_SIMILARITY_SCORE`, `MAX_RETRIEVED_CASES`, or prompt instructions in `backend/utils/memory.py` and `backend/prompts/clinical_prompt.txt`
- **Product UI**: extend `frontend/src/app/` and align API base URL + CORS origins with your deployment

## Non-goals (what is not implemented yet)

- No real EHR login/session handling for production tenants (demos use local mock HTML)
- No durable vector store for clinical memory (Qdrant is in-memory only in this starter)
- No full audit trail or PHI/PII compliance controls (demo starter)
- Authentication/authorization for the Next.js app or BentoML APIs is not included
