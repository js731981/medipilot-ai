from __future__ import annotations

from playwright.sync_api import Page

from actions.labeled import click_button, fill_input
from client.bento_client import BentoWorkflowClient
from core.agent_loop import act, observe, think
from navigation.ehr_navigation import open_mock_ehr


def run_patient_flow(page: Page, *, client: BentoWorkflowClient) -> dict:
    open_mock_ehr(page)
    observation = observe(page)
    result = think(client, observation)

    act(page, result)

    clinical = result.get("clinical") or {}
    coding = result.get("coding") or {}
    diagnoses = clinical.get("diagnosis") or []
    icd_codes = coding.get("icd_codes") or []
    if diagnoses:
        fill_input(page, "Diagnosis", diagnoses[0])
    if icd_codes:
        fill_input(page, "ICD Code", icd_codes[0])

    print("Form filled successfully")
    click_button(page, "Submit")
    print("Form submitted")

    return result

