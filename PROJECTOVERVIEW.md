## Project Overview — medipilot-ai

`medipilot-ai` is a working, end-to-end starter for **EHR browser automation powered by an AI workflow**. It is intentionally “thin but complete”: a backend that turns clinical text into structured extraction + coding suggestions, and a Playwright browser agent that drives a mock EHR page and simulates field entry.

This repo is set up so you can:

- Run locally with deterministic mocks (no API keys required)
- Swap in real LLM calls by adding `OPENAI_API_KEY`
- Replace the mock EHR HTML with your real EHR UI automation targets
- Evolve the workflow into a LangGraph graph later (boundaries already exist)

## Current feature set (complete)

### Backend (BentoML service)

- **Workflow API (default service)**:
  - **`POST /run_full_workflow`**: runs a sequential workflow:
    - Clinical extraction
    - Coding suggestions
    - Output validation
  - **Input**: `{ "text": string, "request_id"?: uuid-string }`
  - **Output**: `{ "request_id": uuid-string, "clinical": {...}, "coding": {...}, "validation": {...} }`
- **Health endpoint**:
  - **`POST /health`** returns `{ status, service, timestamp }` for readiness/liveness checks
- **Deterministic mock mode** (no external dependency):
  - If `OPENAI_API_KEY` is not set, the backend returns deterministic JSON compatible with the prompts, so the system runs end-to-end without network calls.
- **Typed schemas & validation**:
  - Pydantic schemas for `ClinicalEntities`, `CodingSuggestion`, and `WorkflowResult`
  - Validation agent checks required keys/types and confidence range \(0.0..1.0\)
- **Prompt-driven agents**:
  - Prompt templates live under `backend/prompts/`
  - Agents are pure functions under `backend/agents/`
- **Request correlation (`request_id`)**:
  - `request_id` is accepted, normalized, and returned in responses
  - Used for end-to-end log correlation across backend and browser agent

### Workflow implementation

- **Sequential workflow boundaries**:
  - `extract_clinical_entities(text)`
  - `suggest_medical_codes(clinical)`
  - `validate_output({clinical, coding})`
- **LangGraph-ready structure**:
  - Workflow is currently linear but designed with clean boundaries to convert into a graph later.

### Browser agent (Playwright)

- **Mock EHR navigation**:
  - Opens `data/mock_ehr_pages.html` via a local `file://` URL
- **Agent loop (observe → think → act)**:
  - **Observe**: extracts visible text from the page
  - **Think**: calls backend `POST /run_full_workflow`
  - **Act**:
    - Prints the full structured JSON result
    - Fills mock EHR fields if present:
      - `#icd_codes`
      - `#cpt_codes`
      - `#confidence`
- **Resilience**:
  - Backend calls include retries for connection/timeout errors with exponential backoff.
- **Runtime controls**:
  - `HEADLESS=true|false` to control headless browser mode
  - `BACKEND_URL` to target local backend or Docker Compose backend service

### Docker Compose (infra demo)

- **Two services**:
  - `backend`: BentoML service exposed on host port `3000`
  - `browser-agent`: Playwright runner that waits for backend health before starting
- **Healthcheck-gated startup**:
  - Compose healthcheck calls `/health` and only starts browser-agent when backend is healthy.

## Repository map (what lives where)

- **Backend**: `backend/`
  - Service entry: `backend/main.py` (exports `svc`)
  - Workflow service: `backend/services/workflow_service.py`
  - Workflow logic: `backend/workflows/clinical_workflow.py`
  - Agents: `backend/agents/`
  - Prompts: `backend/prompts/`
  - Schemas: `backend/schemas/`
  - Settings: `backend/config/settings.py`
- **Browser agent**: `browser-agent/`
  - Entry: `browser-agent/main.py`
  - Agent loop: `browser-agent/core/agent_loop.py`
  - Workflow wrapper: `browser-agent/workflows/patient_flow.py`
  - Backend client: `browser-agent/client/bento_client.py`
  - Navigation: `browser-agent/navigation/ehr_navigation.py`
- **Mock EHR page**: `data/mock_ehr_pages.html`
- **Docker/compose**: `infra/docker-compose.yml`, `infra/docker/*.Dockerfile`
- **Additional docs**: `docs/`

## APIs (quick reference)

- **Backend base URL**: `http://localhost:3000`
- **`POST /run_full_workflow`**:
  - Request: `{ "text": "..." }` (optionally include `request_id`)
  - Response:
    - `clinical`: `{ symptoms: string[], diagnosis: string[], procedures: string[], confidence: number }`
    - `coding`: `{ icd_codes: string[], cpt_codes: string[], confidence: number }`
    - `validation`: `{ valid: boolean, issues: string[] }`
    - `request_id`: `uuid-string`
- **`POST /health`**:
  - Response: `{ status: "ok", service: "medipilot-ai", timestamp: "..." }`

For the formal spec, see `docs/api-spec.md`.

## Configuration

- **`OPENAI_API_KEY`**:
  - Not set → deterministic mock responses
  - Set → real OpenAI calls via the `openai` SDK
- **`OPENAI_MODEL`**:
  - Defaults to `gpt-4o-mini` if not set
- **`BACKEND_URL`** (browser agent):
  - Defaults to `http://localhost:3000`
  - In Docker Compose: `http://backend:3000`
- **`HEADLESS`** (browser agent):
  - Default: `true` (set `false` to see the browser)

## Extension points (where to add new capabilities)

- **Add more EHR actions**: `browser-agent/actions/` and `browser-agent/navigation/`
- **Improve extraction/coding prompts**: `backend/prompts/`
- **Add new agent steps**:
  - Implement in `backend/agents/`
  - Wire into `backend/workflows/clinical_workflow.py`
- **Convert to a graph workflow**:
  - Replace the sequential workflow with a LangGraph graph while keeping existing agent functions and schemas.

## Non-goals (what is not implemented yet)

- No real EHR login/session handling (the UI is a local mock HTML file)
- No persistent storage, audit trail, or PHI/PII compliance controls (demo starter)
- No UI frontend application (only the Playwright agent + mock HTML page)

