"""Search route."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.dependencies import get_search_service
from src.services.search_service import SearchService
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    """Request body for the search endpoint."""

    query: str
    n_results: int = Field(default=3, ge=1, le=20)


@router.post("")
async def search_files(
    body: SearchRequest,
    svc: SearchService = Depends(get_search_service),
) -> dict[str, Any]:
    """Search indexed files by semantic similarity."""
    logger.info("API search: '%s' n=%d", body.query[:60], body.n_results)
    results = svc.search(body.query, n_results=body.n_results)
    return {
        "results": [
            {
                "file_name": r["file_name"],
                "file_path": r["file_path"],
                "file_type": r["file_type"],
                "preview": r["preview_text"],
                "relevance_score": r["relevance_score"],
                "language": r["language"],
            }
            for r in results
        ],
        "count": len(results),
    }
