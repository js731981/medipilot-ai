from __future__ import annotations

from typing import Any


def validate_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []

    clinical = data.get("clinical", {}) or {}
    coding = data.get("coding", {}) or {}

    for k in ("symptoms", "diagnosis", "procedures"):
        v = clinical.get(k, None)
        if v is None:
            issues.append(f"clinical.{k} missing")
        elif not isinstance(v, list):
            issues.append(f"clinical.{k} must be a list")

    for k in ("icd_codes", "cpt_codes"):
        v = coding.get(k, None)
        if v is None:
            issues.append(f"coding.{k} missing")
        elif not isinstance(v, list):
            issues.append(f"coding.{k} must be a list")

    confidence = coding.get("confidence", None)
    if confidence is None:
        issues.append("coding.confidence missing")
    elif not isinstance(confidence, (int, float)):
        issues.append("coding.confidence must be a number")
    elif not (0.0 <= float(confidence) <= 1.0):
        issues.append("coding.confidence must be between 0.0 and 1.0")

    return {"valid": len(issues) == 0, "issues": issues}

