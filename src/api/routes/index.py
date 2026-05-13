"""Indexing control routes."""

from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_index_service
from src.services.index_service import IndexService
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/index", tags=["index"])

# In-process progress tracker — works correctly for a single uvicorn worker
# (the default for local use). Not safe across multiple workers.
_progress: dict[str, Any] = {
    "running": False,
    "folder": None,
    "done": 0,
    "errors": 0,
}
_progress_lock = threading.Lock()


class IndexRequest(BaseModel):
    """Request body for starting an index operation."""

    folder_path: str


def _run_index(folder_path: str, svc: IndexService) -> None:
    with _progress_lock:
        _progress.update(running=True, folder=folder_path, done=0, errors=0)
    try:
        result = svc.index_folder(folder_path, recursive=True)
        with _progress_lock:
            _progress["done"] = result.get("indexed", 0)
            _progress["errors"] = result.get("errors", 0)
    except Exception as exc:
        logger.error("Indexing error: %s", exc)
    finally:
        with _progress_lock:
            _progress["running"] = False


@router.post("")
async def start_index(
    body: IndexRequest,
    background_tasks: BackgroundTasks,
    svc: IndexService = Depends(get_index_service),
) -> dict:
    """Start indexing a folder in the background."""
    with _progress_lock:
        if _progress["running"]:
            raise HTTPException(409, "Indexing already in progress")
    background_tasks.add_task(_run_index, body.folder_path, svc)
    return {"status": "started", "folder": body.folder_path}


@router.get("/status")
async def index_status(svc: IndexService = Depends(get_index_service)) -> dict:
    """Return current indexing progress."""
    with _progress_lock:
        snap = dict(_progress)
    total = svc.get_count()
    pct = round(snap["done"] / total * 100) if total > 0 else 0
    return {
        "running": snap["running"],
        "folder": snap["folder"],
        "files_done": snap["done"],
        "total_indexed": total,
        "percent": pct,
        "errors": snap["errors"],
    }


@router.delete("")
async def clear_index(svc: IndexService = Depends(get_index_service)) -> dict:
    """Clear the entire index."""
    svc.clear()
    return {"status": "cleared"}
