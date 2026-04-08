from __future__ import annotations

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

