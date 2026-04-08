from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page


def open_mock_ehr(page: Page, html_path: str | None = None) -> None:
    """
    Opens a local mock EHR HTML file (used for demo/testing).
    """
    p = Path(html_path) if html_path else Path(__file__).resolve().parents[2] / "data" / "mock_ehr_pages.html"
    page.goto(p.resolve().as_uri())

