"""Utility helper functions for Talaash."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path


def get_file_size_mb(file_path: str | Path) -> float:
    """Return file size in megabytes."""
    return Path(file_path).stat().st_size / (1024 * 1024)


def get_file_hash(file_path: str | Path) -> str:
    """Return MD5 hash of file contents for change detection."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5.update(chunk)
    return md5.hexdigest()


def chunk_text(text: str, max_chars: int = 1000) -> list[str]:
    """Split text into chunks of at most max_chars characters, respecting word boundaries."""
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end >= len(text):
            chunks.append(text[start:])
            break
        # Try to break at last whitespace within the window
        last_space = text.rfind(" ", start, end)
        if last_space > start:
            end = last_space
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


def clean_text(text: str) -> str:
    """Remove null bytes, excessive whitespace, and non-printable characters."""
    if not text:
        return ""
    # Remove null bytes and control characters except newline/tab
    text = text.replace("\x00", "")
    text = "".join(
        ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t", "\r")
    )
    # Collapse multiple blank lines to at most two
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces/tabs
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 200) -> str:
    """Truncate text to max_chars characters, appending ellipsis if needed."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"
