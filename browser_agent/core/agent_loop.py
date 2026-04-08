from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import Page

from actions.extract import extract_visible_text
from client.bento_client import BentoWorkflowClient


def _maybe_fill(page: Page, selector: str, value: str) -> None:
    loc = page.locator(selector)
    if loc.count() > 0:
        loc.first.fill(value)


def observe(page: Page) -> str:
    return extract_visible_text(page)


def think(client: BentoWorkflowClient, observation: str) -> dict[str, Any]:
    return client.run_full_workflow(observation)


def act(page: Page, result: dict[str, Any]) -> None:
    print("=== AI Workflow Result ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    coding = result.get("coding", {}) or {}
    icd = ", ".join(coding.get("icd_codes", []) or [])
    cpt = ", ".join(coding.get("cpt_codes", []) or [])

    # Simulate form filling on the mock EHR page (if fields exist).
    _maybe_fill(page, "#icd_codes", icd)
    _maybe_fill(page, "#cpt_codes", cpt)
    _maybe_fill(page, "#confidence", str(coding.get("confidence", "")))


def run_agent_loop(page: Page, *, client: BentoWorkflowClient) -> dict[str, Any]:
    observation = observe(page)
    result = think(client, observation)
    act(page, result)
    return result

