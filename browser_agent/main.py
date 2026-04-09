from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent

# Allow running this file directly while still resolving repo-root imports (e.g. `utils.*`)
# and local package imports (e.g. `core.*`).
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_THIS_DIR))

from core.browser import launch_browser  # noqa: E402
from client.bento_client import BentoWorkflowClient  # noqa: E402
from workflows.patient_flow import run_patient_flow  # noqa: E402


def run_browser_automation(data: dict) -> dict:
    # BentoML runs this API in a thread pool; on Windows the default loop in that
    # thread may not support subprocesses, which Playwright needs to start the driver.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    clinical = data["clinical"]
    coding = data["coding"]

    diagnosis = clinical.get("diagnosis", [""])[0]
    icd = coding.get("icd_codes", [""])[0]

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("http://localhost:8000/mock-ehr.html")

        page.fill('input[name="diagnosis"]', diagnosis)
        page.fill('input[name="icd"]', icd)

        page.click('button[type="submit"]')

        print("Form submitted successfully")

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        screenshot_path = os.path.join(BASE_DIR, "output.png")
        page.screenshot(path=screenshot_path)
        print("Screenshot saved")

        browser.close()
        return {
            "status": "success",
            "screenshot_path": screenshot_path,
        }


def main() -> int:
    headless = (os.getenv("HEADLESS", "true").lower() != "false")
    client = BentoWorkflowClient()
    session = launch_browser(headless=headless)
    try:
        run_patient_flow(session.page, client=client)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())

