from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.schemas.clinical_schema import CodingSuggestion
from backend.utils.llm_client import call_llm, safe_json_loads


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "coding_prompt.txt"


def suggest_medical_codes(data: dict[str, Any]) -> dict[str, Any]:
    data_json = json.dumps(data, ensure_ascii=False)
    prompt = _PROMPT_PATH.read_text(encoding="utf-8").replace("{{data_json}}", data_json)
    raw = call_llm(prompt)
    out = safe_json_loads(raw)
    validated = CodingSuggestion.model_validate(out)
    return json.loads(validated.model_dump_json())

