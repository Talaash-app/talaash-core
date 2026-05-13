"""Query normalisation for multilingual input."""

from __future__ import annotations

import re
import unicodedata

# Words that carry zero search meaning when they appear at the START of a query.
# We strip these from the front, stop at the first non-filler word, and pass
# the rest directly to the embedding model — it handles semantics far better
# than any regex ever could.
_LEADING_FILLERS = {
    # Politeness
    "please", "kindly",
    # Action verbs
    "find", "search", "show", "get", "look", "fetch", "give",
    "list", "retrieve", "tell", "display",
    # Modal / helper verbs
    "can", "could", "would", "will", "do", "does",
    # Pronouns / possessives
    "you", "me", "i", "my", "your",
    # Articles / prepositions
    "a", "an", "the", "for", "in", "of", "about",
    # File-related filler nouns
    "file", "files", "document", "documents", "doc", "docs", "folder",
    # Relative words
    "which", "that", "with", "containing", "contains", "has", "have",
    "include", "includes", "including",
    # Quantity words
    "all", "any", "some",
    # Name/label filler
    "name", "names", "named",
}


def extract_search_intent(query: str) -> str:
    """Strip conversational wrapper words, keeping only the searchable content.

    Only strips from the FRONT, stops at the first meaningful token, and never
    touches non-Latin text (Hindi, Marathi, etc.) — those go straight to the
    embedding model unchanged.

    Examples:
        "please find the files which contains the names ramesh kumar"
            → "ramesh kumar"
        "show me my aadhaar card"
            → "aadhaar card"
        "find files with bank statement"
            → "bank statement"
        "bank statement"
            → "bank statement"   (unchanged — no filler at front)
        "मेरा आधार कार्ड"
            → "मेरा आधार कार्ड"  (unchanged — non-Latin)
    """
    if not query:
        return query

    stripped = query.strip()

    # Non-Latin queries (Hindi, Marathi, …) go straight to the model
    if stripped and not stripped[0].isascii():
        return stripped

    words = stripped.split()
    i = 0
    # Always keep at least one word
    while i < len(words) - 1:
        token = words[i].lower().strip(".,!?")
        if token in _LEADING_FILLERS:
            i += 1
        else:
            break

    result = " ".join(words[i:]).strip()
    return result or stripped


def process_query(query: str, detected_language: str) -> str:
    """Normalise a search query for the detected language.

    The underlying multilingual embedding model handles cross-lingual
    similarity internally, so this step focuses on cleaning the text:
    removing extra whitespace, normalising Unicode, and lowercasing
    where appropriate.

    Args:
        query: Raw query string from the user.
        detected_language: ISO 639-1 language code, e.g. "en", "hi", "mr".

    Returns:
        Cleaned query string ready for embedding.
    """
    if not query:
        return ""

    if detected_language in ("hi", "mr"):
        return _normalise_devanagari(query)

    return _normalise_latin(query)


def _normalise_devanagari(text: str) -> str:
    """Normalise Devanagari script text (used for Hindi and Marathi)."""
    # NFC normalisation ensures consistent Unicode form for Devanagari
    text = unicodedata.normalize("NFC", text)
    # Remove zero-width joiners / non-joiners that appear in some encodings
    text = text.replace("‌", "").replace("‍", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalise_latin(text: str) -> str:
    """Normalise Latin-script text (English and similar languages)."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()
