from __future__ import annotations

from playwright.sync_api import Page


def click(page: Page, selector: str) -> None:
    page.click(selector)

