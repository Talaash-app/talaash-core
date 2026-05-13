"""Tests for the search pipeline."""

from __future__ import annotations

from pathlib import Path


def _seed_doc(text: str, path: str, doc_type: str = "unknown", lang: str = "en") -> None:
    """Seed one document into the test-isolated stores via the service layer."""
    from src.services import get_services

    index_svc, _ = get_services()
    embedding = index_svc.embedder.encode(text)
    index_svc.vector_store.add_file(
        file_id=path,
        text=text,
        embedding=embedding,
        metadata={
            "file_name": Path(path).name,
            "file_type": doc_type,
            "language_detected": lang,
            "last_indexed_at": "",
        },
    )
    index_svc.db.save_file_record(
        {
            "file_path": path,
            "file_name": Path(path).name,
            "file_extension": Path(path).suffix,
            "file_size_mb": 0.01,
            "file_hash": "abc123",
            "file_type": doc_type,
            "language_detected": lang,
        }
    )


class TestSearch:
    """End-to-end tests for the SearchService."""

    def test_english_query_returns_results(self) -> None:
        """An English query should find a matching English document."""
        _seed_doc(
            "Bank statement for account holder. Transactions in June.",
            "/docs/bank.pdf",
            doc_type="bank_statement",
            lang="en",
        )
        from src.services import get_services

        _, search_svc = get_services()

        results = search_svc.search("bank statement transactions", n_results=5)
        assert len(results) > 0
        assert results[0]["file_name"] == "bank.pdf"

    def test_hindi_query_returns_results(self) -> None:
        """A Hindi query should find a semantically similar document."""
        _seed_doc(
            "आधार कार्ड। विशिष्ट पहचान प्राधिकरण। UIDAI.",
            "/docs/aadhaar.pdf",
            doc_type="aadhaar_card",
            lang="hi",
        )
        from src.services import get_services

        _, search_svc = get_services()

        results = search_svc.search("मेरा आधार कार्ड", n_results=5)
        assert len(results) > 0

    def test_results_sorted_by_relevance(self) -> None:
        """Results must be ordered by descending relevance_score."""
        _seed_doc("Income tax return ITR assessment year 2023", "/docs/itr.pdf", lang="en")
        _seed_doc("Random file about cooking recipes", "/docs/recipe.txt", lang="en")

        from src.services import get_services

        _, search_svc = get_services()

        results = search_svc.search("income tax return", n_results=5)
        assert len(results) >= 2
        scores = [r["relevance_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_empty_index_returns_empty_list(self) -> None:
        """Searching an empty index must return [], not raise."""
        from src.services import get_services

        _, search_svc = get_services()

        results = search_svc.search("anything at all", n_results=5)
        assert results == []

    def test_empty_query_returns_empty_list(self) -> None:
        """An empty query must return [], not raise."""
        from src.services import get_services

        _, search_svc = get_services()

        results = search_svc.search("", n_results=5)
        assert results == []
