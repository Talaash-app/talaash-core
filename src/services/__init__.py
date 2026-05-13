"""Service layer for src.

Usage (production):
    from src.services import get_services
    index_svc, search_svc = get_services()

Usage (tests / custom config):
    from src.services import create_services
    from src.utils.config import Settings
    svc_pair = create_services(Settings(TALAASH_DB_PATH="/tmp/test_db", ...))
"""

from __future__ import annotations

import threading
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.search.embeddings import Embedder
    from src.services.index_service import IndexService
    from src.services.search_service import SearchService

_index_svc: Optional["IndexService"] = None
_search_svc: Optional["SearchService"] = None
_lock = threading.Lock()


def create_services(
    settings,
    *,
    embedder: Optional["Embedder"] = None,
) -> tuple["IndexService", "SearchService"]:
    """Create a fresh pair of services from the given settings object.

    Args:
        settings: Any object with TALAASH_* attributes (Settings or test override).
        embedder: Optional pre-loaded Embedder to reuse (avoids reloading the model).
    """
    from src.search.embeddings import Embedder
    from src.services.index_service import IndexService
    from src.services.search_service import SearchService
    from src.storage.database import Database
    from src.storage.vector_store import VectorStore

    db = Database(settings.TALAASH_DB_PATH)
    vs = VectorStore(settings.TALAASH_INDEX_PATH)
    if embedder is None:
        embedder = Embedder(settings.TALAASH_MODEL_NAME, settings.TALAASH_BATCH_SIZE)

    index_svc = IndexService(db, vs, embedder)
    search_svc = SearchService(vs, embedder)

    return index_svc, search_svc


def get_services() -> tuple["IndexService", "SearchService"]:
    """Return the module-level singleton services (lazy-created from settings)."""
    global _index_svc, _search_svc
    if _index_svc is None:
        with _lock:
            if _index_svc is None:
                from src.utils.config import settings
                _index_svc, _search_svc = create_services(settings)

    assert _index_svc is not None and _search_svc is not None
    return _index_svc, _search_svc
