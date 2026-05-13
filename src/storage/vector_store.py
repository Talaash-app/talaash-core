"""ChromaDB vector store — VectorStore class."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from src.utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "talaash_files"


class VectorStore:
    """Wraps a ChromaDB persistent collection.

    Construct with an explicit index_path so it can be injected in tests
    without touching module-level globals.
    """

    def __init__(self, index_path: str) -> None:
        path = Path(index_path)
        path.mkdir(parents=True, exist_ok=True)

        try:
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=str(path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        except ImportError:
            self._client = chromadb.PersistentClient(path=str(path))

        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.debug("VectorStore ready at %s", path)

    def add_file(
        self,
        file_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """Upsert a file's vector, document text, and metadata."""
        clean_meta: dict[str, Any] = {
            k: v if isinstance(v, str | int | float | bool) else str(v) for k, v in metadata.items()
        }
        doc_text = text[:32_000] if len(text) > 32_000 else text
        self._collection.upsert(
            ids=[file_id],
            documents=[doc_text],
            embeddings=[embedding],
            metadatas=[clean_meta],
        )
        logger.debug("Upserted vector for %s", file_id)

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Return the n_results nearest vectors with metadata and distance."""
        total = self._collection.count()
        if total == 0:
            return []

        actual_n = min(n_results, total)
        raw = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_n,
            include=["documents", "metadatas", "distances"],
        )

        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        dists = raw.get("distances", [[]])[0]

        return [
            {"id": fid, "document": doc, "metadata": meta, "distance": dist}
            for fid, doc, meta, dist in zip(ids, docs, metas, dists)
        ]

    def delete_file(self, file_id: str) -> None:
        """Remove a vector by its ID."""
        try:
            self._collection.delete(ids=[file_id])
            logger.debug("Deleted vector for %s", file_id)
        except Exception as exc:
            logger.warning("Could not delete vector %s: %s", file_id, exc)

    def get_count(self) -> int:
        """Return the total number of indexed vectors."""
        return self._collection.count()

    def clear(self) -> None:
        """Wipe and recreate the collection."""
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("VectorStore cleared")
