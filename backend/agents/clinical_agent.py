from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from backend.schemas.clinical_schema import ClinicalEntities
from backend.utils.llm_client import call_llm, safe_json_loads


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "clinical_prompt.txt"

_CLARITY_KEYWORDS = ("complaint", "fever", "pain", "diagnosis", "history")
_BOILERPLATE_MARKERS = (
    "this page simulates",
    "for demonstration purposes",
    "mock data",
    "sample data",
    "simulation",
)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _compute_confidence(text: str, *, symptoms: list[str], diagnosis: list[str], procedures: list[str]) -> float:
    t = (text or "").strip()
    if not t:
        return 0.0

    low = t.lower()
    keyword_hits = sum(1 for k in _CLARITY_KEYWORDS if k in low)
    keyword_score = _clamp(keyword_hits / 3.0)  # 0..1 after ~3 hits

    # Reward having enough context, without overweighting long text.
    length_score = _clamp(len(t) / 400.0)

    # Penalize obvious non-clinical boilerplate.
    boilerplate_penalty = 0.25 if any(m in low for m in _BOILERPLATE_MARKERS) else 0.0

    # Entity density: more extracted entities generally means higher confidence.
    entity_count = len(symptoms) + len(diagnosis) + len(procedures)
    entity_score = _clamp(entity_count / 8.0)

    # Simple heuristic blend.
    clarity = _clamp(0.55 * keyword_score + 0.45 * length_score - boilerplate_penalty)
    confidence = _clamp(0.15 + 0.55 * clarity + 0.30 * entity_score, 0.0, 0.99)

    # Avoid claiming high confidence if the input is extremely noisy (e.g., mostly symbols).
    alpha_ratio = (len(re.findall(r"[A-Za-z]", t)) / max(1, len(t)))
    if alpha_ratio < 0.35:
        confidence = min(confidence, 0.4)

    return float(round(confidence, 3))


def extract_clinical_entities(text: str) -> dict[str, Any]:
    prompt = _PROMPT_PATH.read_text(encoding="utf-8").replace("{{text}}", text)
    raw = call_llm(prompt)
    data = safe_json_loads(raw)
    validated = ClinicalEntities.model_validate(data)
    confidence = _compute_confidence(
        text,
        symptoms=validated.symptoms,
        diagnosis=validated.diagnosis,
        procedures=validated.procedures,
    )
    validated.confidence = confidence
    return json.loads(validated.model_dump_json())

