"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_search_service
from src.services.search_service import SearchService

router = APIRouter()
VERSION = "0.1.0"


@router.get("/health", tags=["health"])
async def health(svc: SearchService = Depends(get_search_service)) -> dict:
    """Return service status, version, and count of indexed files."""
    return {
        "status": "ok",
        "version": VERSION,
        "indexed_files": svc.get_count(),
    }
