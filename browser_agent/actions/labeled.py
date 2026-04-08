from __future__ import annotations

from playwright.sync_api import Locator, Page


def get_input_by_label(page: Page, label: str) -> Locator:
    """
    Locate an input, textarea, or select using:
    - accessible label (get_by_label),
    - placeholder (get_by_placeholder), or
    - a wrapping <label> whose text includes *label* (get_by_text).
    """
    by_label = page.get_by_label(label)
    by_placeholder = page.get_by_placeholder(label)
    by_wrapping_label = page.locator("label").filter(has=page.get_by_text(label)).locator(
        "input, textarea, select"
    )
    return by_label.or_(by_placeholder).or_(by_wrapping_label)


def fill_input(page: Page, label: str, value: str) -> None:
    """Find a field by label / placeholder / wrapping label text and fill *value*."""
    get_input_by_label(page, label).fill(value)


def click_button(page: Page, name: str) -> None:
    """Find a control with role *button* whose subtree contains *name* and click it."""
    page.get_by_role("button").filter(has=page.get_by_text(name)).click()
