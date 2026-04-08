## Architecture

`medipilot-ai` is split into two runnable components:

- **Backend (BentoML)**: exposes JSON APIs for clinical extraction, coding, and a full workflow.
- **Browser Agent (Playwright)**: loads an EHR-like page, extracts visible text, calls the backend workflow, and simulates filling code fields.

### Data flow

1. Browser agent opens `data/mock_ehr_pages.html`
2. Observe: extract page text
3. Think: POST to BentoML `run_full_workflow`
4. Act: print structured output + fill mock form fields

### Extensibility

- Agents are pure Python functions in `backend/agents/`
- Workflow orchestration is in `backend/workflows/` and is structured to be LangGraph-ready

