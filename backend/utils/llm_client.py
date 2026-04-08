from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI

from backend.utils.logger import get_logger


logger = get_logger(__name__, level=os.getenv("LOG_LEVEL", "INFO"))


def _mock_response(prompt: str) -> str:
    prompt_lower = prompt.lower()

    if "icd_codes" in prompt_lower or "cpt_codes" in prompt_lower:
        return json.dumps(
            {
                "icd_codes": ["R07.9", "J18.9"],
                "cpt_codes": ["99213"],
                "confidence": 0.74,
            }
        )

    if re.search(r"\"symptoms\"\s*:", prompt) or "extract symptoms" in prompt_lower:
        return json.dumps(
            {
                "symptoms": ["cough", "fever", "chest pain"],
                "diagnosis": ["community-acquired pneumonia"],
                "procedures": ["chest x-ray"],
            }
        )

    return json.dumps({"message": "mock_response"})


def call_llm(prompt: str) -> str:
    """
    Call OpenAI with a single prompt. If OPENAI_API_KEY is missing,
    returns a deterministic mock JSON string compatible with prompts.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _mock_response(prompt)

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise medical extraction and coding assistant.\n"
                    "Output must be a single JSON object only (no markdown, no code fences, no extra text)."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    content = resp.choices[0].message.content or ""
    return content.strip()


def safe_json_loads(text: str) -> dict[str, Any]:
    """
    Best-effort JSON parse for LLM outputs that may include fences.
    """
    cleaned = (text or "").strip().lstrip("\ufeff")
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    def _as_dict(obj: Any) -> dict[str, Any]:
        return obj if isinstance(obj, dict) else {}

    try:
        return _as_dict(json.loads(cleaned))
    except Exception:
        pass

    # If the model added extra prose, try to extract the first JSON object.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = cleaned[start : end + 1]
        try:
            return _as_dict(json.loads(snippet))
        except Exception:
            pass

    logger.warning("Failed to parse JSON from model output; falling back to empty object.")
    return {}

