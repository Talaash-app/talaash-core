"""Plain text extractor with WhatsApp chat support."""

from __future__ import annotations

import re
from typing import Any

from src.extractor.base import BaseExtractor
from src.utils.helpers import clean_text
from src.utils.logger import get_logger

logger = get_logger(__name__)

# WhatsApp message timestamp pattern:  dd/mm/yyyy, hh:mm - Name: message
_WHATSAPP_LINE_RE = re.compile(
    r"^\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?:\s*[AP]M)?\s*-\s*[^:]+:\s*",
    re.IGNORECASE,
)
_WHATSAPP_HEADER_RE = re.compile(
    r"^\[?\d{1,2}/\d{1,2}/\d{2,4},?\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?\]?\s*-?"
)


def _looks_like_whatsapp(lines: list[str]) -> bool:
    """Heuristic: true if >30% of lines look like WhatsApp timestamps."""
    if len(lines) < 5:
        return False
    hits = sum(1 for line in lines[:50] if _WHATSAPP_LINE_RE.match(line))
    return hits / min(len(lines), 50) > 0.3


def _strip_whatsapp(text: str) -> str:
    """Remove WhatsApp timestamp headers, keeping only message bodies."""
    lines = text.splitlines()
    clean_lines: list[str] = []
    for line in lines:
        stripped = _WHATSAPP_LINE_RE.sub("", line).strip()
        if stripped and stripped not in ("<Media omitted>", "This message was deleted"):
            clean_lines.append(stripped)
    return "\n".join(clean_lines)


class TextExtractor(BaseExtractor):
    """Extract text from plain .txt files, with special handling for WhatsApp exports."""

    def extract(self, file_path: str) -> dict[str, Any]:
        """Read a plain text file, auto-detecting encoding.

        Tries UTF-8 first, then falls back to latin-1. Detects WhatsApp chat
        exports and strips timestamp/phone-number headers to preserve only
        message content.
        """
        raw: str = ""
        encoding_used = "utf-8"

        try:
            with open(file_path, encoding="utf-8") as f:
                raw = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, encoding="latin-1") as f:
                    raw = f.read()
                encoding_used = "latin-1"
            except Exception as exc:
                return self._fail(f"Cannot read file: {exc}")
        except Exception as exc:
            return self._fail(f"Cannot open file: {exc}")

        try:
            lines = raw.splitlines()
            is_whatsapp = _looks_like_whatsapp(lines)
            if is_whatsapp:
                text = _strip_whatsapp(raw)
                metadata = {"encoding": encoding_used, "source": "whatsapp_export"}
            else:
                text = raw
                metadata = {"encoding": encoding_used, "source": "plain_text"}

            return self._ok(clean_text(text), metadata)

        except Exception as exc:
            logger.warning("Text extraction error for %s: %s", file_path, exc)
            return self._fail(str(exc))
