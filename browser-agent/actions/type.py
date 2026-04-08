from __future__ import annotations

from playwright.sync_api import Page


def type_text(page: Page, selector: str, text: str) -> None:
    page.fill(selector, text)

