from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents.clinical_agent import extract_clinical_entities
from backend.agents.coding_agent import suggest_medical_codes
from backend.agents.validation_agent import validate_output
from backend.utils.logger import get_logger, get_request_id


logger = get_logger(__name__)


def _log_running_node(node_name: str) -> None:
    rid = get_request_id()
    suffix = f" request_id={rid}" if rid else ""
    logger.info("Running %s node%s", node_name, suffix)


class WorkflowState(TypedDict):
    input_text: str
    clinical: dict
    coding: dict
    validation: dict
    memory_used: bool


def clinical_node(state: WorkflowState) -> dict[str, Any]:
    _log_running_node("clinical")
    clinical, memory_used = extract_clinical_entities(state["input_text"])
    return {**state, "clinical": clinical, "memory_used": memory_used}


def coding_node(state: WorkflowState) -> dict[str, Any]:
    _log_running_node("coding")
    coding = suggest_medical_codes(state["clinical"])
    return {**state, "coding": coding}


def validation_node(state: WorkflowState) -> dict[str, Any]:
    _log_running_node("validation")
    combined = {"clinical": state["clinical"], "coding": state["coding"]}
    validation = validate_output(combined)
    return {**state, "validation": validation}


graph = StateGraph(WorkflowState)
graph.add_node("clinical", clinical_node)
graph.add_node("coding", coding_node)
graph.add_node("validation", validation_node)
graph.add_edge(START, "clinical")
graph.add_edge("clinical", "coding")
graph.add_edge("coding", "validation")
graph.add_edge("validation", END)
workflow = graph.compile()


def run_langgraph_workflow(text: str):
    initial_state = {
        "input_text": text,
        "clinical": {},
        "coding": {},
        "validation": {},
        "memory_used": False,
    }

    result = workflow.invoke(initial_state)

    return result
