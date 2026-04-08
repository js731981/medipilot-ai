from __future__ import annotations

from typing import Any

from backend.agents.clinical_agent import extract_clinical_entities
from backend.agents.coding_agent import suggest_medical_codes
from backend.agents.validation_agent import validate_output


def run_workflow(text: str, *, request_id: str | None = None) -> dict[str, Any]:
    clinical = extract_clinical_entities(text)
    coding = suggest_medical_codes(clinical)
    combined = {"clinical": clinical, "coding": coding}
    validation = validate_output(combined)
    # Keep request_id available in downstream logs via context; return payload stays focused.
    _ = request_id
    return {**combined, "validation": validation}

