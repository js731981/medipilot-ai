from __future__ import annotations

import base64
import os
from pathlib import Path

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
            logs = [
                "Clinical agent executed",
                "Memory searched",
                "Coding agent executed",
                "Validation completed",
            ]
            logger.info("run_full_workflow.done")

        return {
            "request_id": request_id,
            "clinical": result["clinical"],
            "coding": result["coding"],
            "validation": result["validation"],
            "logs": logs,
        }

    @bentoml.api(route="/run_browser_automation", input_spec=dict, output_spec=dict)
    def run_browser_automation_api(self, root: dict) -> dict:
        from browser_agent.main import run_browser_automation

        result = run_browser_automation(root)

        return {
            "status": "success",
            "message": "Automation completed",
            "screenshot_path": result.get("screenshot_path", ""),
        }

    @bentoml.api(
        route="/get_screenshot",
    )
    def get_screenshot(self) -> dict:
        import os, base64

        file_path = os.path.join("browser_agent", "output.png")

        if not os.path.exists(file_path):
            return {"error": "Screenshot not found"}

        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return {
            "image": encoded
        }


workflow_svc = _WorkflowService

