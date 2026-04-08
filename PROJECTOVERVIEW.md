## Project Overview — medipilot-ai

`medipilot-ai` is a working, end-to-end starter for **EHR browser automation powered by an AI workflow**. It is intentionally “thin but complete”: a backend that turns clinical text into structured extraction + coding suggestions, and a Playwright browser agent that drives a mock EHR page and simulates field entry.

This repo is set up so you can:

- Run locally with deterministic mocks (no API keys required)
- Swap in real LLM calls by adding `OPENAI_API_KEY`
- Replace the mock EHR HTML with your real EHR UI automation targets
- Use a **LangGraph**-compiled workflow for the default `run_full_workflow` path (with optional similar-case retrieval from in-memory vector memory)

## Current feature set (complete)

### Backend (BentoML service)

- **Workflow API (default service)**:
  - **`POST /run_full_workflow`**: runs a sequential workflow:
    - Clinical extraction
    - Coding suggestions
    - Output validation
  - **Input**: `{ "text": string, "request_id"?: uuid-string }`
  - **Output**: `{ "request_id": uuid-string, "clinical": {...}, "coding": {...}, "validation": {...}, "memory_used": boolean }`
    - **`memory_used`**: `true` when the clinical step injected non-empty similar-case text into the LLM prompt (see **Clinical vector memory** below); `false` when no case met the similarity threshold or retrieval failed.
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
- **Clinical vector memory** (`backend/utils/memory.py`):
  - **Qdrant** client over **`:memory:`** (no disk persistence; resets when the process exits).
  - **`store_case`**: embeds clinical note text (OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` is set, otherwise a deterministic mock embedding), stores diagnosis, optional codes, confidence, timestamp.
  - **`search_similar_cases`**: cosine similarity search; results sorted by score (descending); **at most 3** cases returned; default gate **`score > MIN_SIMILARITY_SCORE` (0.7)** — callers may override via `min_score`.
  - **`retrieve_similar_cases_text`**: returns a **plain-text** block for prompts (not JSON), e.g. labeled lines for symptoms (from stored text), diagnosis, confidence, and date.
  - When no point passes the threshold after search, the module logs **`No relevant memory found`** at INFO (ensure your logging config shows `backend.utils.memory`).
- **Clinical extraction prompt** (`clinical_prompt.txt`):
  - Sections: **Patient data** (current note), **Relevant past cases** (from memory or empty), **Instructions** (use past cases only if relevant; do not blindly copy diagnosis; prioritize current patient data), plus explicit reasoning guidance to reduce retrieval bias.
- **Request correlation (`request_id`)**:
  - `request_id` is accepted, normalized, and returned in responses
  - Used for end-to-end log correlation across backend and browser agent

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
  - Service entry: `backend/main.py` (exports `svc` → workflow service by default)
  - Workflow service: `backend/services/workflow_service.py`
  - Workflow logic: **`backend/workflows/langgraph_workflow.py`** (default path for `run_full_workflow`)
  - Alternate workflow: `backend/workflows/clinical_workflow.py`
  - Agents: `backend/agents/` (e.g. `clinical_agent.py`, `coding_agent.py`, `validation_agent.py`)
  - Vector memory utilities: `backend/utils/memory.py`
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
    - **`memory_used`**: boolean — whether similar-case text was included in the clinical LLM prompt
    - `request_id`: `uuid-string`
- **`POST /extract_clinical_data`** (when the clinical Bento service is mounted):
  - Response merges the clinical entity object with **`memory_used`** in one JSON object.
- **`POST /health`**:
  - Response: `{ status: "ok", service: "medipilot-ai", timestamp: "..." }`

For the formal spec, see `docs/api-spec.md`.

## Configuration

- **`OPENAI_API_KEY`**:
  - Not set → deterministic mock responses
  - Set → real OpenAI calls via the `openai` SDK
- **`OPENAI_MODEL`**:
  - Defaults to `gpt-4o-mini` if not set
- **`OPENAI_EMBEDDING_MODEL`** (optional):
  - Used for vector memory when `OPENAI_API_KEY` is set; defaults to `text-embedding-3-small` (must match embedding size configured in `memory.py`)
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
  - Wire into `backend/workflows/langgraph_workflow.py` (and/or `clinical_workflow.py` if you keep that graph in sync)
- **Tune retrieval**:
  - Adjust `MIN_SIMILARITY_SCORE`, `MAX_RETRIEVED_CASES`, or prompt instructions in `backend/utils/memory.py` and `backend/prompts/clinical_prompt.txt`

## Non-goals (what is not implemented yet)

- No real EHR login/session handling (the UI is a local mock HTML file)
- No durable vector store for clinical memory (Qdrant is in-memory only in this starter)
- No full audit trail or PHI/PII compliance controls (demo starter)
- No UI frontend application (only the Playwright agent + mock HTML page)

