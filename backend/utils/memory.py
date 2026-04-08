from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PointStruct,
    Range,
    VectorParams,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "clinical_cases"
VECTOR_SIZE = 1536
MAX_RETRIEVED_CASES = 3
# Cosine similarity from Qdrant; only cases strictly above this are returned.
MIN_SIMILARITY_SCORE = 0.7


def _get_client() -> QdrantClient:
    return QdrantClient(":memory:")


_client: QdrantClient | None = None
_collection_ready = False


def _client_singleton() -> QdrantClient:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


def _ensure_collection() -> QdrantClient:
    global _collection_ready
    client = _client_singleton()
    if not _collection_ready:
        names = {c.name for c in client.get_collections().collections}
        if COLLECTION_NAME not in names:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
        _collection_ready = True
    return client


def _mock_embedding(text: str, dim: int = VECTOR_SIZE) -> list[float]:
    """Deterministic pseudo-embedding when OPENAI_API_KEY is unset."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    rng = int.from_bytes(digest[:16], "big") or 1
    vec: list[float] = []
    for _ in range(dim):
        rng = (rng * 6364136223846793005 + 1) & ((1 << 64) - 1)
        vec.append((rng / float(1 << 64)) * 2.0 - 1.0)
    norm = sum(x * x for x in vec) ** 0.5
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def _embed_text(text: str) -> list[float]:
    stripped = (text or "").strip()
    if not stripped:
        stripped = " "

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _mock_embedding(stripped)

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    resp = client.embeddings.create(model=model, input=stripped)
    vector = list(resp.data[0].embedding)
    if len(vector) != VECTOR_SIZE:
        raise ValueError(
            f"Embedding dimension {len(vector)} != {VECTOR_SIZE}; "
            "use a 1536-d model (e.g. text-embedding-3-small) or adjust VECTOR_SIZE."
        )
    return vector


def _normalize_diagnosis(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        s = raw.strip()
        return [s] if s else []
    if isinstance(raw, list):
        out: list[str] = []
        for x in raw:
            s = str(x).strip()
            if s:
                out.append(s)
        return out
    s = str(raw).strip()
    return [s] if s else []


def _normalize_confidence(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return max(0.0, min(1.0, v))


def _build_search_filter(
    *,
    min_confidence: float | None,
    since_epoch: float | None,
    diagnosis_any: list[str] | None,
) -> Filter | None:
    must: list[FieldCondition] = []
    if min_confidence is not None:
        must.append(FieldCondition(key="confidence", range=Range(gte=float(min_confidence))))
    if since_epoch is not None:
        must.append(FieldCondition(key="ts", range=Range(gte=float(since_epoch))))
    if diagnosis_any:
        must.append(FieldCondition(key="diagnosis", match=MatchAny(any=diagnosis_any)))
    if not must:
        return None
    return Filter(must=must)


def _hit_similarity_score(hit: Any) -> float:
    s = getattr(hit, "score", None)
    if not isinstance(s, (int, float)) or s != s:
        return float("-inf")
    return float(s)


def _case_dict_similarity(c: dict[str, Any]) -> float:
    s = c.get("score")
    if isinstance(s, (int, float)) and s == s:
        return float(s)
    return float("-inf")


def _format_timestamp_display(raw: Any) -> str:
    if raw is None:
        return "—"
    s = str(raw).strip()
    if not s:
        return "—"
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except ValueError:
        return s


def _symptoms_line_from_text(text: str, *, max_chars: int) -> str:
    t = (text or "").strip()
    if not t:
        return "—"
    line = " ".join(t.split())
    line = line.replace("\n", ", ")
    while ", ," in line:
        line = line.replace(", ,", ",")
    if len(line) > max_chars:
        line = line[: max_chars - 3].rstrip() + "..."
    return line or "—"


def _normalize_diagnosis_filter(raw: str | list[str] | None) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        s = raw.strip()
        return [s] if s else None
    out = [str(x).strip() for x in raw if str(x).strip()]
    return out or None


def store_case(data: dict[str, Any]) -> str:
    """
    Store a clinical case with embedding over ``text`` and rich payload metadata.

    Keys:
      - text (str): note text used for the vector
      - diagnosis (list | str): diagnoses
      - codes (list): optional codes
      - confidence (float, optional): 0..1; stored for filtering and display
    """
    text = str(data.get("text", "") or "")
    diagnosis = _normalize_diagnosis(data.get("diagnosis"))
    codes = data.get("codes") or []
    if not isinstance(codes, list):
        codes = list(codes) if codes is not None else []
    codes = [str(c).strip() for c in codes if str(c).strip()]
    conf = _normalize_confidence(data.get("confidence"))

    now = datetime.now(timezone.utc)
    ts = now.timestamp()
    timestamp_iso = now.isoformat()

    client = _ensure_collection()
    point_id = str(uuid.uuid4())
    vector = _embed_text(text)

    payload: dict[str, Any] = {
        "text": text,
        "diagnosis": diagnosis,
        "codes": codes,
        "timestamp": timestamp_iso,
        "ts": ts,
    }
    if conf is not None:
        payload["confidence"] = conf

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )
    return point_id


def search_similar_cases(
    text: str,
    *,
    limit: int = 3,
    min_score: float | None = None,
    min_confidence: float | None = None,
    since_epoch: float | None = None,
    diagnosis_match: str | list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Vector search with optional payload filters (Qdrant ``must`` conditions).

    Results are sorted by similarity score (highest first) and capped at
    :data:`MAX_RETRIEVED_CASES` (3). By default only points with similarity
    **strictly greater** than :data:`MIN_SIMILARITY_SCORE` (0.7) are returned;
    pass ``min_score`` to use a different cutoff (same strict ``>`` rule).

    - min_score: if ``None``, uses :data:`MIN_SIMILARITY_SCORE`.
    - min_confidence: only points with stored confidence >= this value.
    - since_epoch: only points stored at or after this Unix time.
    - diagnosis_match: only points whose ``diagnosis`` list overlaps these strings.
    """
    client = _ensure_collection()
    vector = _embed_text(text)
    q_filter = _build_search_filter(
        min_confidence=min_confidence,
        since_epoch=since_epoch,
        diagnosis_any=_normalize_diagnosis_filter(diagnosis_match),
    )

    thr = float(MIN_SIMILARITY_SCORE if min_score is None else min_score)

    want = min(max(1, limit), MAX_RETRIEVED_CASES)
    # Extra headroom; post-filter by score for consistent behavior across client versions.
    fetch_limit = max(want, want * 4)

    kwargs: dict[str, Any] = {
        "collection_name": COLLECTION_NAME,
        "limit": fetch_limit,
    }
    if q_filter is not None:
        kwargs["query_filter"] = q_filter

    if hasattr(client, "query_points"):
        kwargs["query"] = vector
        hits = client.query_points(**kwargs).points
    else:
        kwargs["query_vector"] = vector
        hits = client.search(**kwargs)

    hits = sorted(hits, key=_hit_similarity_score, reverse=True)

    hits = [
        h
        for h in hits
        if getattr(h, "score", None) is not None and float(h.score) > thr
    ]
    hits = hits[:want]

    if not hits:
        logger.info("No relevant memory found")

    out: list[dict[str, Any]] = []
    for h in hits:
        payload = h.payload or {}
        conf = _normalize_confidence(payload.get("confidence"))
        out.append(
            {
                "text": payload.get("text", ""),
                "diagnosis": _normalize_diagnosis(payload.get("diagnosis")),
                "codes": payload.get("codes") or [],
                "timestamp": payload.get("timestamp"),
                "confidence": conf,
                "score": h.score,
            }
        )
    return out


def format_cases_as_context(cases: list[dict[str, Any]], *, max_text_chars: int = 400) -> str:
    """
    Build a readable plain-text block for prompts (no JSON).

    Each case uses stored note text as ``Symptoms``, payload diagnoses, optional
    confidence, and a YYYY-MM-DD timestamp. At most the first
    :data:`MAX_RETRIEVED_CASES` entries are shown; pass cases already sorted by
    similarity (as from :func:`search_similar_cases`). Returns ``""`` when
    ``cases`` is empty.
    """
    if not cases:
        return ""

    ordered = sorted(cases[:MAX_RETRIEVED_CASES], key=_case_dict_similarity, reverse=True)

    blocks: list[str] = []
    for i, c in enumerate(ordered, start=1):
        symptoms = _symptoms_line_from_text(str(c.get("text") or ""), max_chars=max_text_chars)

        dx = c.get("diagnosis") or []
        dx_s = ", ".join(str(x) for x in dx) if dx else "—"

        conf = c.get("confidence")
        if conf is None:
            conf_s = "—"
        else:
            conf_s = f"{float(conf):.2f}"

        ts_s = _format_timestamp_display(c.get("timestamp"))

        blocks.append(
            f"Case {i}:\n"
            f"Symptoms: {symptoms}\n"
            f"Diagnosis: {dx_s}\n"
            f"Confidence: {conf_s}\n"
            f"Timestamp: {ts_s}"
        )
    return "\n\n".join(blocks)


def retrieve_similar_cases_text(
    text: str,
    *,
    min_score: float | None = None,
    min_confidence: float | None = None,
    since_epoch: float | None = None,
    diagnosis_match: str | list[str] | None = None,
    max_symptom_chars: int = 400,
) -> str:
    """
    Search and return a single human-readable string (top matches, best similarity first).
    Returns an empty string when nothing exceeds the similarity threshold.
    """
    cases = search_similar_cases(
        text,
        limit=MAX_RETRIEVED_CASES,
        min_score=min_score,
        min_confidence=min_confidence,
        since_epoch=since_epoch,
        diagnosis_match=diagnosis_match,
    )
    return format_cases_as_context(cases, max_text_chars=max_symptom_chars)


__all__ = [
    "COLLECTION_NAME",
    "MAX_RETRIEVED_CASES",
    "MIN_SIMILARITY_SCORE",
    "VECTOR_SIZE",
    "format_cases_as_context",
    "retrieve_similar_cases_text",
    "search_similar_cases",
    "store_case",
]
