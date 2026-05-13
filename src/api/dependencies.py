"""FastAPI dependency providers for the service layer."""

from __future__ import annotations

from src.services import get_services
from src.services.index_service import IndexService
from src.services.search_service import SearchService


def get_index_service() -> IndexService:
    """FastAPI dependency: return the singleton IndexService."""
    index_svc, _ = get_services()
    return index_svc


def get_search_service() -> SearchService:
    """FastAPI dependency: return the singleton SearchService."""
    _, search_svc = get_services()
    return search_svc
