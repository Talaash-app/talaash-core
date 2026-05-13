"""Abstract base class for all text extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseExtractor(ABC):
    """Contract that all file extractors must satisfy."""

    @abstractmethod
    def extract(self, file_path: str) -> dict[str, Any]:
        """Extract text and metadata from a file.

        Args:
            file_path: Absolute or relative path to the file.

        Returns:
            dict with keys:
                text (str): Extracted plain text.
                metadata (dict): Extra info from the file (title, author, …).
                success (bool): True if extraction succeeded.
                error (str | None): Error message if success is False.
        """

    def _ok(self, text: str, metadata: dict | None = None) -> dict[str, Any]:
        """Convenience factory for a successful result."""
        return {
            "text": text,
            "metadata": metadata or {},
            "success": True,
            "error": None,
        }

    def _fail(self, error: str, metadata: dict | None = None) -> dict[str, Any]:
        """Convenience factory for a failed result."""
        return {
            "text": "",
            "metadata": metadata or {},
            "success": False,
            "error": error,
        }
