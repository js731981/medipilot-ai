## Architecture Overview — medipilot-ai

This document describes the current, working architecture of `medipilot-ai`: a **Next.js UI** that calls a **BentoML backend** to run an AI workflow and trigger **Playwright browser automation**, plus a **screenshot retrieval** route that returns base64 so the UI can render automation proof reliably.

## High-level system view

**Runtime components (local dev defaults):**

- **Frontend (Next.js)**: `http://localhost:3000`
- **Backend (BentoML)**: `http://localhost:3001`
- **Mock EHR static server (http.server)**: `http://localhost:8000`
- **Browser agent (Playwright)**: launched by either:
  - the backend (`POST /run_browser_automation`), or
  - the CLI (`python browser_agent/main.py`)

**Primary user flow:**

1. User pastes clinical note in the UI and clicks **Run AI**
2. UI calls backend `POST /run_full_workflow`
3. Backend returns structured `clinical`, `coding`, and `validation` objects + logs
4. User clicks **Approve**
5. UI calls backend `POST /run_browser_automation` (backend launches Playwright)
6. UI calls backend `POST /get_screenshot` and renders it from base64 as a `data:` URL

## Architecture diagram (components + flows)

```mermaid
flowchart LR
  U[User] -->|Run AI / Approve| FE[Next.js Frontend\nfrontend/src/app/page.tsx\n:3000]

  FE -->|POST /run_full_workflow\n{text}| BE[BentoML Backend\nbackend/main.py → workflow service\n:3001]
  BE -->|runs workflow| WF[LangGraph workflow\nbackend/workflows/langgraph_workflow.py]
  WF --> CL[Clinical agent\nbackend/agents/clinical_agent.py]
  WF --> CD[Coding agent\nbackend/agents/coding_agent.py]
  WF --> VL[Validation agent\nbackend/agents/validation_agent.py]
  CL <-->|retrieve/store similar cases| MEM[Vector memory\nbackend/utils/memory.py\n(Qdrant :memory:)]

  FE -->|POST /run_browser_automation\n{clinical,coding}| BE
  BE -->|imports & runs| BA[Playwright browser agent\nbrowser_agent/main.py\nrun_browser_automation()]
  BA -->|HTTP GET| EHR[Mock EHR page\nbrowser_agent/mock-ehr.html\nserved by http.server\n:8000]
  BA -->|writes screenshot| PNG[(browser_agent/output.png)]

  FE -->|POST /get_screenshot| BE
  BE -->|reads + base64 encodes| PNG
  BE -->|{ image: base64 }| FE
```

## Repository layout (exact map)

This is the functional layout the code follows today (key files only).

```text
medipilot-ai/
  ARCHITECTUREOVERVIEW.md
  PROJECTOVERVIEW.md
  README.md

  backend/
    main.py
    requirements.txt
    services/
      workflow_service.py
    workflows/
      langgraph_workflow.py
      clinical_workflow.py
    agents/
      clinical_agent.py
      coding_agent.py
      validation_agent.py
    prompts/
      clinical_prompt.txt
      coding_prompt.txt
      validation_prompt.txt
    schemas/
      # pydantic models (clinical/coding/validation)
    utils/
      memory.py
      logger.py
    config/
      settings.py

  browser_agent/
    main.py
    output.png
    mock-ehr.html
    actions/
    client/
    core/
    navigation/
    workflows/

  data/
    mock_ehr_pages.html

  frontend/
    README.md
    package.json
    src/
      app/
        page.tsx

  docs/
    architecture.md
    workflows.md
    api-spec.md

  infra/
    docker-compose.yml
    docker/
      # Dockerfiles
```

## Backend architecture (BentoML)

The backend is a BentoML service responsible for:

- **Workflow execution**: transform free-text clinical notes into structured output.
- **Automation orchestration**: trigger the Playwright browser agent and return a status result.
- **Screenshot serving**: return the latest automation screenshot as base64 JSON for frontend rendering.

### Service entrypoint

- **`backend/main.py`** exports the BentoML service (`svc`) and configures middleware (notably CORS for the dev frontend origin).

### Workflow service

- **`backend/services/workflow_service.py`** defines the API routes used by the UI:
  - **`POST /run_full_workflow`**
    - Input: `{ text, request_id? }`
    - Output: `{ request_id, clinical, coding, validation, logs }` (and other fields depending on the workflow implementation)
  - **`POST /run_browser_automation`**
    - Input: `{ clinical, coding }` (typically the objects returned by `run_full_workflow`)
    - Behavior: imports and runs `browser_agent.main.run_browser_automation()`
  - **`POST /get_screenshot`**
    - Behavior: reads `browser_agent/output.png`, base64-encodes the bytes, returns `{ image: "<base64>" }`
  - **`POST /health`**
    - Output: `{ status: "ok", service: "medipilot-ai" }`

### Workflow engine (LangGraph)

- **`backend/workflows/langgraph_workflow.py`** is the default “full workflow” pipeline.
- The workflow is conceptually linear:
  - **Clinical extraction** → **Coding suggestions** → **Validation**
- Each step is implemented as an agent function under `backend/agents/`.

### Clinical memory (in-process vector retrieval)

- **`backend/utils/memory.py`** provides “similar case” retrieval using an **in-memory Qdrant** instance.
- The clinical step may:
  - embed the incoming note,
  - retrieve up to a small number of similar cases above a similarity threshold,
  - inject retrieved text into the clinical prompt.

This is designed to provide lightweight retrieval augmentation in a dev-friendly way (no external DB required by default).

## Browser agent architecture (Playwright)

The browser agent is the subsystem that drives the mock EHR UI and produces `browser_agent/output.png`.

### Two execution modes

1. **API-driven automation** (the “Approve” flow)
   - Triggered by backend `POST /run_browser_automation`
   - Opens the mock EHR over HTTP:
     - **`http://localhost:8000/mock-ehr.html`**
   - Fills form fields from the `clinical` / `coding` payload
   - Submits the form
   - Saves a screenshot to `browser_agent/output.png`

2. **CLI demo loop**
   - Run manually with `python browser_agent/main.py`
   - Often opens the file-based mock EHR:
     - `data/mock_ehr_pages.html` via `file://...`

### Why screenshots are served as base64 JSON

The UI does **not** hotlink the PNG using `<img src="http://backend/...">`:

- Instead, it calls `POST /get_screenshot`, receives JSON `{ image: "<base64>" }`,
- then renders it as:
  - `data:image/png;base64,<base64>`

This pattern is typically more reliable in dev (and easier to control) because it avoids:

- cross-origin image fetch quirks,
- caching surprises (you can add cache-busting later if needed),
- and makes the backend contract explicit.

## Frontend architecture (Next.js)

- The UI lives in **`frontend/src/app/page.tsx`** (single page in the current starter).
- It maintains UI state for:
  - input text,
  - workflow result,
  - status + logs,
  - screenshot (as a base64 `data:` URL string).

### Key frontend requests (current)

- **Run AI**
  - `POST http://localhost:3001/run_full_workflow`
  - Body: `{ text }`
- **Approve**
  - `POST http://localhost:3001/run_browser_automation`
  - Body: `{ clinical, coding }`
  - then `POST http://localhost:3001/get_screenshot`
  - Response: `{ image }`, used to set:
    - `setScreenshot("data:image/png;base64," + image)`

## End-to-end sequence (Approve path)

```mermaid
sequenceDiagram
  participant U as User
  participant FE as Frontend (Next.js :3000)
  participant BE as Backend (BentoML :3001)
  participant BA as Browser Agent (Playwright)
  participant EHR as Mock EHR (:8000)
  participant FS as Filesystem (workspace)

  U->>FE: Click "Run AI"
  FE->>BE: POST /run_full_workflow {text}
  BE-->>FE: {clinical, coding, validation, logs}

  U->>FE: Click "Approve"
  FE->>BE: POST /run_browser_automation {clinical, coding}
  BE->>BA: run_browser_automation()
  BA->>EHR: Load /mock-ehr.html
  BA->>EHR: Fill fields + submit
  BA->>FS: Write browser_agent/output.png
  BE-->>FE: {status: "success", ...}

  FE->>BE: POST /get_screenshot
  BE->>FS: Read browser_agent/output.png
  BE-->>FE: {image: "<base64>"}
  FE-->>U: Render <img src="data:image/png;base64,...">
```

## Operational notes (local dev)

- **Ports**
  - Frontend: `3000`
  - Backend: `3001` (matches current frontend fetch URLs)
  - Mock EHR: `8000`
- **Mock EHR server is required** for `/run_browser_automation`
  - Serve `browser_agent/` on `8000` so `mock-ehr.html` is accessible.
- **Screenshot availability**
  - `POST /get_screenshot` returns `{ error: "Screenshot not found" }` until the browser agent has written `browser_agent/output.png`.

