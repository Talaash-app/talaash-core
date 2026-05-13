"""Result ranking for Talaash search."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Document-type keywords that hint at query intent
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "aadhaar_card": ["aadhaar", "aadhar", "uid", "आधार"],
    "pan_card": ["pan", "income tax", "पैन"],
    "passport": ["passport", "पासपोर्ट"],
    "voter_id": ["voter", "election", "मतदाता"],
    "driving_license": ["driving", "license", "licence", "ड्राइविंग"],
    "bank_statement": ["bank", "statement", "account", "बैंक"],
    "salary_slip": ["salary", "payslip", "वेतन"],
    "itr": ["itr", "income tax return", "आयकर"],
    "form_16": ["form 16", "tds", "tax deducted"],
    "marksheet": ["mark", "marks", "result", "अंकपत्र"],
    "insurance": ["insurance", "policy", "बीमा"],
    "rental_agreement": ["rent", "tenant", "landlord", "किरायानामा"],
}

_LANGUAGE_BOOST = 0.05
_TYPE_BOOST = 0.10
_RECENCY_MAX_BOOST = 0.05
_RECENCY_HALF_LIFE_DAYS = 365


def rank_results(
    raw_results: list[dict[str, Any]],
    query: str,
    language: str,
) -> list[dict[str, Any]]:
    """Re-rank raw ChromaDB results using additional signals.

    Signals applied on top of the cosine similarity score:
      - Document type matches query intent → small boost
      - Document language matches query language → small boost
      - Recently modified files → small recency boost

    Args:
        raw_results: Output of vector_store.search().
        query: Original query string (used for type-intent matching).
        language: Detected language of the query.

    Returns:
        Results sorted by descending final_score, each enriched with a
        relevance_score key (0-100 integer).
    """
    query_lower = query.lower()
    now = datetime.now(UTC)

    scored: list[dict[str, Any]] = []
    for result in raw_results:
        distance = result.get("distance", 1.0)
        # Cosine distance from ChromaDB: 0 = identical, 2 = opposite
        # Convert to a 0-1 similarity score
        similarity = max(0.0, 1.0 - distance / 2.0)

        meta = result.get("metadata", {})
        doc_type = meta.get("file_type", "unknown")
        doc_lang = meta.get("language_detected", "en")
        last_indexed_str = meta.get("last_indexed_at", "")

        # Language boost
        lang_boost = _LANGUAGE_BOOST if doc_lang == language else 0.0

        # Document type intent boost
        type_boost = 0.0
        for dtype, keywords in _TYPE_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                if doc_type == dtype:
                    type_boost = _TYPE_BOOST
                break

        # Recency boost (exponential decay)
        recency_boost = 0.0
        if last_indexed_str:
            try:
                if isinstance(last_indexed_str, datetime):
                    last_dt = last_indexed_str
                else:
                    last_dt = datetime.fromisoformat(str(last_indexed_str))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=UTC)
                age_days = (now - last_dt).days
                recency_boost = _RECENCY_MAX_BOOST * math.exp(-age_days / _RECENCY_HALF_LIFE_DAYS)
            except Exception:
                pass

        final_score = min(1.0, similarity + lang_boost + type_boost + recency_boost)
        result = dict(result)
        result["final_score"] = final_score
        result["relevance_score"] = round(final_score * 100)
        scored.append(result)

    scored.sort(key=lambda r: r["final_score"], reverse=True)
    logger.debug("Ranked %d results", len(scored))
    return scored
