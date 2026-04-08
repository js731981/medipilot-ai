from __future__ import annotations

from pydantic import BaseModel, Field


class ClinicalEntities(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    diagnosis: list[str] = Field(default_factory=list)
    procedures: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class CodingSuggestion(BaseModel):
    icd_codes: list[str] = Field(default_factory=list)
    cpt_codes: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class WorkflowResult(BaseModel):
    clinical: ClinicalEntities
    coding: CodingSuggestion
    validation: dict

