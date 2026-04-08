from __future__ import annotations

from typing import Any, TypedDict

from backend.agents.clinical_agent import extract_clinical_entities
from backend.agents.coding_agent import suggest_medical_codes
from backend.agents.validation_agent import validate_output


class ClinicalWorkflowState(TypedDict):
    request_id: str
    input_text: str
    clinical: dict
    coding: dict
    validation: dict


def clinical_node(state: ClinicalWorkflowState) -> dict[str, Any]:
    clinical = extract_clinical_entities(state["input_text"])
    return {"clinical": clinical}


def coding_node(state: ClinicalWorkflowState) -> dict[str, Any]:
    coding = suggest_medical_codes(state["clinical"])
    return {"coding": coding}


def validation_node(state: ClinicalWorkflowState) -> dict[str, Any]:
    combined = {"clinical": state["clinical"], "coding": state["coding"]}
    validation = validate_output(combined)
    return {"validation": validation}


def build_clinical_workflow_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(ClinicalWorkflowState)
    graph.add_node("clinical", clinical_node)
    graph.add_node("coding", coding_node)
    graph.add_node("validation", validation_node)

    graph.add_edge(START, "clinical")
    graph.add_edge("clinical", "coding")
    graph.add_edge("coding", "validation")
    graph.add_edge("validation", END)

    return graph.compile()


_CLINICAL_WORKFLOW_GRAPH = build_clinical_workflow_graph()


def run_workflow(text: str, *, request_id: str | None = None) -> ClinicalWorkflowState:
    rid = request_id or "unknown"

    initial_state: ClinicalWorkflowState = {
        "request_id": rid,
        "input_text": text,
        "clinical": {},
        "coding": {},
        "validation": {},
    }
    final_state = _CLINICAL_WORKFLOW_GRAPH.invoke(initial_state)
    return final_state

