from __future__ import annotations

import bentoml

from backend.agents.clinical_agent import extract_clinical_entities


@bentoml.service(name="clinical_service")
class _ClinicalService:
    @bentoml.api(input_spec=dict, output_spec=dict)
    def extract_clinical_data(self, payload: dict) -> dict:
        text = payload.get("text", "")
        return extract_clinical_entities(text)


clinical_svc = _ClinicalService

