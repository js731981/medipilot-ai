from __future__ import annotations

import bentoml

from uuid import UUID, uuid4

from backend.workflows.langgraph_workflow import run_langgraph_workflow
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
    @bentoml.api(route="/health")
    def health(self) -> dict:
        return {
            "status": "ok",
            "service": "medipilot-ai"
        }

    @bentoml.api(input_spec=dict, output_spec=dict)
    def run_full_workflow(self, root: dict) -> dict:
        text = root.get("text", "")
        request_id = _normalize_request_id(root.get("request_id")) or str(uuid4())

        with request_context(request_id=request_id):
            logger.info("run_full_workflow.start")
            result = run_langgraph_workflow(text)
            logger.info("run_full_workflow.done")

        return {
            "request_id": request_id,
            "clinical": result["clinical"],
            "coding": result["coding"],
            "validation": result["validation"],
        }


workflow_svc = _WorkflowService

