from __future__ import annotations

import json
import re
from typing import Any

from playwright.sync_api import Page


def _normalize_ws(s: str) -> str:
    return " ".join((s or "").split())


_DOB_RE = re.compile(
    r"\b(?:dob|date\s*of\s*birth|birthdate)\b\s*[:\-]?\s*(?P<date>\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    re.IGNORECASE,
)

_NAME_RE = re.compile(
    r"\bname\b\s*[:\-]\s*(?P<name>[A-Za-z][A-Za-z'.-]*(?:\s+[A-Za-z][A-Za-z'.-]*){1,4})\b",
    re.IGNORECASE,
)

_CLINICAL_KEYWORDS = ["complaint", "fever", "pain", "diagnosis", "history"]


def _looks_like_ui_meta(text: str) -> bool:
    t = _normalize_ws(text).lower()
    if not t:
        return True
    if len(t) <= 2:
        return True
    if len(t) < 12 and t in {"ok", "cancel", "close", "next", "back", "submit", "search"}:
        return True

    ui_markers = [
        "cookie",
        "privacy",
        "terms",
        "all rights reserved",
        "copyright",
        "powered by",
        "sign in",
        "log in",
        "login",
        "create account",
        "forgot password",
        "help center",
        "contact us",
        "home",
        "menu",
        "navigation",
        "settings",
        "language",
        "loading",
        "error",
        "warning",
    ]
    return any(m in t for m in ui_markers)


def _looks_like_non_clinical_boilerplate(text: str) -> bool:
    t = _normalize_ws(text).lower()
    if not t:
        return True
    boilerplate_markers = [
        "this page simulates",
        "simulates a",
        "simulation",
        "demo page",
        "for demonstration purposes",
        "sample data",
        "mock data",
        "fictitious",
        "not real patient",
    ]
    return any(m in t for m in boilerplate_markers)


def _has_required_clinical_keyword(text: str) -> bool:
    t = _normalize_ws(text).lower()
    return any(k in t for k in _CLINICAL_KEYWORDS)


def _extract_field_from_inputs(
    inputs: list[dict[str, Any]],
    *,
    label_patterns: list[re.Pattern[str]],
    value_patterns: list[re.Pattern[str]] | None = None,
) -> str | None:
    best: str | None = None
    best_score = -1
    for inp in inputs or []:
        label = _normalize_ws(str(inp.get("label") or ""))
        value = _normalize_ws(str(inp.get("value") or ""))
        if not (label or value):
            continue

        score = 0
        for p in label_patterns:
            if p.search(label):
                score += 2
        if value_patterns:
            for p in value_patterns:
                if p.search(value):
                    score += 1

        if score > best_score:
            best_score = score
            best = value or None

    return best if best_score > 0 else None


def _extract_medical_lines(paragraphs: list[str]) -> list[str]:
    kept: list[str] = []
    seen: set[str] = set()

    for p in paragraphs or []:
        s = _normalize_ws(p)
        if not s:
            continue
        if _looks_like_ui_meta(s):
            continue
        if _looks_like_non_clinical_boilerplate(s):
            continue
        if not _has_required_clinical_keyword(s):
            continue

        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(s)

    return kept


def build_clinical_text(extracted_data: dict) -> str:
    """
    Convert structured extraction output into a natural clinical narrative.
    Expects keys like: title, paragraphs, inputs.
    """
    paragraphs: list[str] = list(extracted_data.get("paragraphs") or [])
    inputs: list[dict[str, Any]] = list(extracted_data.get("inputs") or [])

    name = _extract_field_from_inputs(
        inputs,
        label_patterns=[
            re.compile(r"\bpatient\s*name\b", re.IGNORECASE),
            re.compile(r"\bname\b", re.IGNORECASE),
            re.compile(r"\bfirst\s*name\b", re.IGNORECASE),
            re.compile(r"\blast\s*name\b", re.IGNORECASE),
        ],
    )
    dob = _extract_field_from_inputs(
        inputs,
        label_patterns=[
            re.compile(r"\bdob\b", re.IGNORECASE),
            re.compile(r"\bdate\s*of\s*birth\b", re.IGNORECASE),
            re.compile(r"\bbirth\s*date\b", re.IGNORECASE),
            re.compile(r"\bbirthdate\b", re.IGNORECASE),
        ],
        value_patterns=[
            re.compile(r"^\d{4}-\d{2}-\d{2}$"),
            re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$"),
        ],
    )
    chief_complaint = _extract_field_from_inputs(
        inputs,
        label_patterns=[
            re.compile(r"\bchief\s*complaint\b", re.IGNORECASE),
            re.compile(r"\breason\s*for\s*visit\b", re.IGNORECASE),
            re.compile(r"\bpresenting\s*complaint\b", re.IGNORECASE),
            re.compile(r"\bcomplaint\b", re.IGNORECASE),
        ],
    )

    joined_paras = "\n".join(paragraphs or [])
    if not name:
        m = _NAME_RE.search(joined_paras)
        if m:
            candidate = _normalize_ws(m.group("name"))
            if candidate and not _looks_like_ui_meta(candidate) and not _looks_like_non_clinical_boilerplate(candidate):
                name = candidate
    if not dob:
        m = _DOB_RE.search(joined_paras)
        if m:
            dob = _normalize_ws(m.group("date"))
    if not chief_complaint:
        m = re.search(
            r"\b(?:chief\s*complaint|reason\s*for\s*visit|presenting\s*complaint)\b\s*[:\-]?\s*(?P<cc>.+)",
            joined_paras,
            re.IGNORECASE,
        )
        if m:
            chief_complaint = _normalize_ws(m.group("cc"))
            chief_complaint = re.split(r"[.;]\s+", chief_complaint, maxsplit=1)[0].strip()

    medical_lines = _extract_medical_lines(paragraphs)

    if name and _looks_like_ui_meta(name):
        name = None
    if name and _looks_like_non_clinical_boilerplate(name):
        name = None

    lines: list[str] = []

    # Patient details (allowed even if they don't contain the required keywords).
    patient_line = "Patient"
    if name:
        patient_line += f" {name}"
    if dob:
        patient_line += f", DOB {dob}"
    patient_line += "."
    lines.append(patient_line)

    # Medical info (must be keyword-matching).
    if chief_complaint and _has_required_clinical_keyword(f"complaint {chief_complaint}"):
        lines.append(f"Complaint: {chief_complaint}")

    cc_low = (chief_complaint or "").lower()
    for line in medical_lines:
        if cc_low and cc_low in line.lower():
            continue
        lines.append(line)

    # Ensure no non-clinical boilerplate slips through.
    lines = [l for l in lines if not _looks_like_non_clinical_boilerplate(l)]

    return "\n".join(lines).strip()


def _extract_raw_text(page: Page) -> str:
    body_text = page.inner_text("body")
    field_values: list[str] = page.eval_on_selector_all(
        "textarea, input",
        "els => els.map(e => (e.value || '').toString()).filter(Boolean)",
    )
    combined = "\n".join([body_text, *field_values])
    return _normalize_ws(combined)


def _extract_structured(page: Page) -> dict[str, Any]:
    title = _normalize_ws(page.title() or "")

    headings: dict[str, list[str]] = {
        "h1": [
            _normalize_ws(t)
            for t in (page.eval_on_selector_all("h1", "els => els.map(e => e.innerText)") or [])
            if _normalize_ws(t)
        ],
        "h2": [
            _normalize_ws(t)
            for t in (page.eval_on_selector_all("h2", "els => els.map(e => e.innerText)") or [])
            if _normalize_ws(t)
        ],
    }

    paragraphs = [
        _normalize_ws(t)
        for t in (page.eval_on_selector_all("p", "els => els.map(e => e.innerText)") or [])
        if _normalize_ws(t)
    ]

    # Collect input/textarea/select fields with a best-effort label.
    inputs: list[dict[str, Any]] = page.eval_on_selector_all(
        "input, textarea, select",
        """
        els => els.map(el => {
          const norm = (s) => (s || '').toString().replace(/\\s+/g, ' ').trim();

          const tag = (el.tagName || '').toLowerCase();
          const type = tag === 'input' ? (el.getAttribute('type') || 'text').toLowerCase() : tag;
          const id = el.getAttribute('id') || '';
          const name = el.getAttribute('name') || '';

          const ariaLabel = el.getAttribute('aria-label') || '';
          const ariaLabelledBy = el.getAttribute('aria-labelledby') || '';
          let labelledByText = '';
          if (ariaLabelledBy) {
            labelledByText = ariaLabelledBy
              .split(/\\s+/)
              .map(id => document.getElementById(id))
              .filter(Boolean)
              .map(n => n.innerText || n.textContent || '')
              .join(' ');
          }

          let labelText = '';
          if (el.labels && el.labels.length) {
            labelText = Array.from(el.labels)
              .map(l => l.innerText || l.textContent || '')
              .join(' ');
          } else if (id) {
            const explicit = document.querySelector(`label[for="${CSS.escape(id)}"]`);
            if (explicit) labelText = explicit.innerText || explicit.textContent || '';
          }

          const placeholder = el.getAttribute('placeholder') || '';

          let value = '';
          if (tag === 'select') {
            const opt = el.selectedOptions && el.selectedOptions[0];
            value = opt ? (opt.value || opt.textContent || '') : (el.value || '');
          } else if (type === 'checkbox' || type === 'radio') {
            value = el.checked ? (el.value || 'true') : '';
          } else {
            value = el.value || '';
          }

          const label = norm(labelText) || norm(ariaLabel) || norm(labelledByText) || norm(placeholder) || norm(name) || norm(id);

          return {
            tag,
            type,
            id: id || null,
            name: name || null,
            label: label || null,
            value: norm(value) || null
          };
        })
        """,
    )

    # Drop completely unlabeled + empty fields; keep others.
    inputs = [i for i in inputs if i.get("label") or i.get("value")]

    return {
        "title": title,
        "headings": headings,
        "paragraphs": paragraphs,
        "inputs": inputs,
    }


def extract_visible_text(page: Page) -> str:
    """
    Returns a JSON string with extracted page content:
    - title
    - headings (h1, h2)
    - paragraphs
    - input field labels + values

    If structured parsing fails, falls back to raw visible text.
    """
    try:
        payload: dict[str, Any] = _extract_structured(page)
        clinical_text = build_clinical_text(payload)
        final_payload: dict[str, Any] = {"raw": payload, "clinical_text": clinical_text}
        text = json.dumps(final_payload, ensure_ascii=False)
        print("FINAL CLINICAL TEXT:")
        print(clinical_text)
    except Exception:
        raw = _extract_raw_text(page)
        final_payload = {"raw": {"text": raw}, "clinical_text": raw}
        text = json.dumps(final_payload, ensure_ascii=False)
        print("FINAL CLINICAL TEXT:")
        print(raw)

    print(f"EXTRACTED TEXT LENGTH: {len(text)}")
    print(f"EXTRACTED TEXT PREVIEW: {text[:300]}")
    return text

