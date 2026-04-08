from __future__ import annotations

import bentoml

from backend.agents.coding_agent import suggest_medical_codes


@bentoml.service(name="coding_service")
class _CodingService:
    @bentoml.api(input_spec=dict, output_spec=dict)
    def suggest_codes(self, payload: dict) -> dict:
        data = payload.get("data", {}) or {}
        return suggest_medical_codes(data)


coding_svc = _CodingService

