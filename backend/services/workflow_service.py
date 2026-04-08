from __future__ import annotations

import bentoml

from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.workflows.clinical_workflow import run_workflow
from backend.utils.logger import get_logger, request_context


logger = get_logger(__name__)


def _normalize_request_id(value: object) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        try:
            return str(UUID(value))
        except ValueError:
            return None
    return None


@bentoml.service(name="workflow_service")
class _WorkflowService:
    @bentoml.api(route="/health", input_spec=dict, output_spec=dict)
    def health(self, _: dict) -> dict:
        return {
            "status": "ok",
            "service": "medipilot-ai",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @bentoml.api(input_spec=dict, output_spec=dict)
    def run_full_workflow(self, payload: dict) -> dict:
        text = payload.get("text", "")
        request_id = _normalize_request_id(payload.get("request_id")) or str(uuid4())

        with request_context(request_id=request_id):
            logger.info("run_full_workflow.start")
            out = run_workflow(text, request_id=request_id)
            logger.info("run_full_workflow.done")

        # Include request_id in the response for end-to-end correlation.
        return {"request_id": request_id, **out}


workflow_svc = _WorkflowService

