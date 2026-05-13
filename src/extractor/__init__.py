"""Extractor factory for src."""

from __future__ import annotations

from pathlib import Path

from src.extractor.base import BaseExtractor


def get_extractor(file_path: str) -> BaseExtractor | None:
    """Return the appropriate extractor for the given file, or None if unsupported.

    Args:
        file_path: Path to the file whose extractor is needed.

    Returns:
        A BaseExtractor instance or None.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        from src.extractor.pdf import PDFExtractor
        return PDFExtractor()

    if ext == ".docx":
        from src.extractor.docx import DocxExtractor
        return DocxExtractor()

    if ext == ".txt":
        from src.extractor.text import TextExtractor
        return TextExtractor()

    if ext in {".png", ".jpg", ".jpeg"}:
        from src.extractor.image import ImageExtractor
        return ImageExtractor()

    return None
