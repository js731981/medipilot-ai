## API Spec (BentoML)

Base URL (local): `http://localhost:3000`

### `POST /run_full_workflow`

**Request JSON**

- `text`: string

**Response JSON**

- `clinical`: `{ symptoms: string[], diagnosis: string[], procedures: string[] }`
- `coding`: `{ icd_codes: string[], cpt_codes: string[], confidence: number }`
- `validation`: `{ valid: boolean, issues: string[] }`

### `POST /extract_clinical_data` (optional service)

Exposed in `backend/services/clinical_service.py` when serving that service module.

### `POST /suggest_codes` (optional service)

Exposed in `backend/services/coding_service.py` when serving that service module.

