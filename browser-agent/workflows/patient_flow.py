from __future__ import annotations

from playwright.sync_api import Page

from core.agent_loop import run_agent_loop
from client.bento_client import BentoWorkflowClient
from navigation.ehr_navigation import open_mock_ehr


def run_patient_flow(page: Page, *, client: BentoWorkflowClient) -> dict:
    open_mock_ehr(page)
    return run_agent_loop(page, client=client)

