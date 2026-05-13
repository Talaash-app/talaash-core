"""Sentence-transformers embedding model — Embedder class."""

from __future__ import annotations

import threading

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Embedder:
    """Loads and wraps a sentence-transformers model.

    The model is loaded lazily on the first encode call. Call load() at
    application startup to pre-warm it so the first query is fast.

    Thread-safe: model loading is protected by a lock; inference is safe
    to call from multiple threads concurrently.
    """

    def __init__(self, model_name: str, batch_size: int = 10) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        self._model = None
        self._lock = threading.Lock()

    def load(self) -> None:
        """Pre-warm the model. Call once at application startup."""
        self._get_model()

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    print(
                        f"\n[Talaash] Loading embedding model '{self._model_name}'...\n"
                        "  First run downloads ~470 MB. Subsequent runs use the cache.\n"
                    )
                    self._model = SentenceTransformer(self._model_name)
                    print("[Talaash] Model ready.\n")
                    logger.info("Embedder model '%s' loaded", self._model_name)
        return self._model

    def encode(self, text: str) -> list[float]:
        """Encode a single text string into a normalised embedding vector."""
        model = self._get_model()
        return model.encode(text, convert_to_numpy=True, normalize_embeddings=True).tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts in one batched call for indexing efficiency."""
        if not texts:
            return []
        model = self._get_model()
        embeddings = model.encode(
            texts,
            batch_size=self._batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [e.tolist() for e in embeddings]
