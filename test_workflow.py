from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from uuid import uuid4

import requests


DEFAULT_BASE_URL = os.getenv("MEDIPILOT_API_BASE_URL", "http://localhost:3000").rstrip("/")
DEFAULT_ENDPOINT = "/run_full_workflow"


SAMPLE_CLINICAL_TEXT = (
    "45M presents with 3 days of fever, productive cough, and mild chest pain. "
    "Exam: crackles RLL. Plan: chest X-ray, start antibiotics. "
    "Impression: community-acquired pneumonia."
)


def _pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)


def _print_section(title: str, value: Any) -> None:
    print()
    print(f"== {title} ==")
    if value is None:
        print("(missing)")
        return
    if isinstance(value, (dict, list)):
        print(_pretty(value))
        return
    print(str(value))


def call_workflow_api(*, base_url: str, endpoint: str, text: str, timeout_s: float) -> dict:
    url = f"{base_url}{endpoint}"
    payload = {"text": text, "request_id": str(uuid4())}
    resp = requests.post(url, json=payload, timeout=timeout_s)

    try:
        data = resp.json()
    except ValueError as e:  # includes JSONDecodeError
        raise RuntimeError(
            f"API returned non-JSON response (status={resp.status_code}). "
            f"First 500 chars:\n{resp.text[:500]}"
        ) from e

    if not resp.ok:
        raise RuntimeError(
            "API request failed "
            f"(status={resp.status_code}, reason={resp.reason}). "
            f"Body:\n{_pretty(data) if isinstance(data, (dict, list)) else str(data)}"
        )

    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response type: {type(data).__name__}. Body:\n{_pretty(data)}")

    return data


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Send sample clinical text to the BentoML workflow API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help=f"Endpoint path (default: {DEFAULT_ENDPOINT})")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds (default: 30)")
    parser.add_argument(
        "--text",
        default=SAMPLE_CLINICAL_TEXT,
        help="Clinical note text (default: built-in sample).",
    )
    args = parser.parse_args(argv)

    try:
        out = call_workflow_api(
            base_url=args.base_url,
            endpoint=args.endpoint,
            text=args.text,
            timeout_s=args.timeout,
        )
    except requests.exceptions.ConnectionError as e:
        print(
            "ERROR: Could not connect to the API.\n"
            f"- base_url: {args.base_url}\n"
            "Make sure the backend is running, e.g.:\n"
            '  bentoml serve backend.main:svc --host 0.0.0.0 --port 3000\n',
            file=sys.stderr,
        )
        print(f"Details: {e}", file=sys.stderr)
        return 2
    except requests.exceptions.Timeout as e:
        print(f"ERROR: Request timed out after {args.timeout:.1f}s.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return 3
    except requests.RequestException as e:
        print("ERROR: Request failed.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return 4
    except Exception as e:
        print("ERROR: Workflow call failed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1

    _print_section("request_id", out.get("request_id"))
    _print_section("clinical", out.get("clinical"))
    _print_section("coding", out.get("coding"))
    _print_section("validation", out.get("validation"))
    _print_section("full_response", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
