"""Document type classifier for Indian government and financial documents."""

from __future__ import annotations

from pathlib import Path

from src.documents.indian_docs import INDIAN_DOC_PATTERNS
from src.utils.logger import get_logger

logger = get_logger(__name__)


def classify_document(text: str, filename: str) -> str:
    """Classify a document into a known Indian document type.

    Classification is attempted first from text content (keyword matching),
    then from the filename if text classification returns "unknown".

    Args:
        text: Extracted text content of the file.
        filename: Basename of the file (used as fallback).

    Returns:
        Document type string (e.g. "aadhaar_card") or "unknown".
    """
    doc_type = _classify_from_text(text)
    if doc_type == "unknown" and filename:
        doc_type = _classify_from_filename(filename)
    logger.debug("Classified '%s' as '%s'", filename, doc_type)
    return doc_type


def _classify_from_text(text: str) -> str:
    """Score each document type against extracted text keywords."""
    if not text:
        return "unknown"

    lower_text = text.lower()
    best_type = "unknown"
    best_score = 0

    for doc_type, keywords in INDIAN_DOC_PATTERNS.items():
        score = sum(1 for kw in keywords if kw.lower() in lower_text)
        if score > best_score:
            best_score = score
            best_type = doc_type

    # Require at least 2 keyword hits to avoid false positives
    return best_type if best_score >= 2 else "unknown"


def _classify_from_filename(filename: str) -> str:
    """Try to infer document type from common filename patterns."""
    stem = Path(filename).stem.lower()
    filename_hints: dict[str, list[str]] = {
        "aadhaar_card": ["aadhaar", "aadhar", "uid"],
        "pan_card": ["pan", "pan_card"],
        "passport": ["passport"],
        "voter_id": ["voter", "epic"],
        "driving_license": ["driving", "dl", "license", "licence"],
        "bank_statement": ["statement", "bank", "account"],
        "salary_slip": ["salary", "payslip", "pay_slip"],
        "itr": ["itr", "income_tax_return"],
        "form_16": ["form16", "form_16"],
        "marksheet": ["marksheet", "mark_sheet", "result", "marks"],
        "insurance": ["insurance", "policy"],
        "rental_agreement": ["rent", "rental", "lease"],
    }
    for doc_type, hints in filename_hints.items():
        if any(hint in stem for hint in hints):
            return doc_type
    return "unknown"
