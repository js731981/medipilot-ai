from __future__ import annotations

import json
import os
import time
from typing import Any
from uuid import uuid4

import requests

from utils.logger import get_logger, request_context

logger = get_logger(__name__)


class BentoWorkflowClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("BACKEND_URL") or "http://localhost:3000").rstrip("/")

    def run_full_workflow(self, text: str) -> dict[str, Any]:
        extracted_data: dict[str, Any] | None = None
        try:
            extracted_data = json.loads(text)
        except Exception:
            extracted_data = None

        text_to_send = (
            str((extracted_data or {}).get("clinical_text") or "").strip()
            if isinstance(extracted_data, dict)
            else ""
        )
        if not text_to_send:
            text_to_send = text

        logger.info("TEXT SENT TO AI:")
        logger.info("%s", text_to_send)

        url = f"{self.base_url}/run_full_workflow"
        request_id = str(uuid4())
        resp = self._post_with_retries(
            url,
            json={"text": text_to_send, "request_id": request_id},
            timeout=60,
            request_id=request_id,
        )
        resp.raise_for_status()
        return resp.json()

    def _post_with_retries(
        self,
        url: str,
        *,
        json: dict[str, Any],
        timeout: int | float,
        request_id: str | None = None,
    ) -> requests.Response:
        max_attempts = 5
        backoff_seconds = 1.0
        last_exc: Exception | None = None

        with request_context(request_id=request_id):
            for attempt in range(1, max_attempts + 1):
                try:
                    return requests.post(url, json=json, timeout=timeout)
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                    last_exc = exc
                    if attempt >= max_attempts:
                        break

                    logger.warning(
                        "Bento API call failed (attempt %s/%s). Retrying in %ss. url=%s error=%r",
                        attempt,
                        max_attempts,
                        int(backoff_seconds) if backoff_seconds.is_integer() else backoff_seconds,
                        url,
                        exc,
                    )
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2

        raise RuntimeError(
            f"Failed to call Bento API after {max_attempts} attempts due to repeated connection/timeout errors. url={url} request_id={request_id} last_error={last_exc!r}"
        )

