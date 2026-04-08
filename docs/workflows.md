## Workflows

### Clinical workflow (`backend/workflows/clinical_workflow.py`)

Steps:

1. **Clinical extraction**: `extract_clinical_entities(text)`
2. **Coding suggestion**: `suggest_medical_codes(clinical_entities)`
3. **Validation**: `validate_output({clinical, coding})`

The workflow is currently sequential and intentionally simple, but the boundaries (agents + typed schemas) make it straightforward to convert into a LangGraph graph later.

