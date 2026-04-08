from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


@dataclass
class BrowserSession:
    playwright: Playwright
    browser: Browser
    page: Page

    def close(self) -> None:
        try:
            self.browser.close()
        finally:
            self.playwright.stop()


def launch_browser(*, headless: bool = True) -> BrowserSession:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    return BrowserSession(playwright=pw, browser=browser, page=page)

