"""SearchService — owns all search business logic."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.languages.detector import detect_language
from src.languages.processor import extract_search_intent, process_query
from src.search.ranking import rank_results
from src.utils.helpers import truncate_text
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.search.embeddings import Embedder
    from src.storage.vector_store import VectorStore

logger = get_logger(__name__)


class SearchService:
    """Orchestrates the full search pipeline.

    Steps: intent extraction → language detection → query normalisation
           → embedding → vector search → re-ranking → result formatting.

    Injected dependencies allow swapping the vector store or embedder
    in tests without touching module-level globals.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
    ) -> None:
        self.vector_store = vector_store
        self.embedder = embedder

    def search(
        self,
        query: str,
        n_results: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search indexed files by semantic similarity to query.

        Args:
            query: Natural-language query in any supported language.
            n_results: Maximum number of results to return.
            filters: Reserved for future metadata filtering.

        Returns:
            List of result dicts ordered by relevance_score descending.
        """
        if not query or not query.strip():
            return []

        intent = extract_search_intent(query)
        language = detect_language(intent)
        logger.info("Search | query='%s' intent='%s' lang=%s", query[:60], intent[:60], language)

        normalised = process_query(intent, language)
        embedding = self.embedder.encode(normalised)

        raw = self.vector_store.search(embedding, n_results=n_results)
        if not raw:
            return []

        ranked = rank_results(raw, query, language)
        return [self._format_result(r, language) for r in ranked]

    def get_count(self) -> int:
        """Return total number of indexed files."""
        return self.vector_store.get_count()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _format_result(self, item: dict[str, Any], query_language: str) -> dict[str, Any]:
        """Convert a ranked ChromaDB result into a clean result dict."""
        meta = item.get("metadata", {})
        doc_text = item.get("document", "")
        return {
            "file_name": meta.get("file_name", Path(item["id"]).name),
            "file_path": item["id"],
            "file_type": meta.get("file_type", "unknown"),
            "language": meta.get("language_detected", query_language),
            "preview_text": truncate_text(doc_text, 200),
            "relevance_score": item.get("relevance_score", 0),
            "last_modified": meta.get("last_indexed_at", ""),
        }
