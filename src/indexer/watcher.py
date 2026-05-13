"""Folder watcher — accepts IndexService as a dependency."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from src.utils.config import settings
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.services.index_service import IndexService

logger = get_logger(__name__)


class _Handler(FileSystemEventHandler):
    """React to filesystem events by updating the index."""

    def __init__(self, index_service: "IndexService") -> None:
        self._svc = index_service

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if not event.is_directory and self._is_supported(event.src_path):
            logger.info("New file: %s", event.src_path)
            self._svc.index_file(event.src_path)

    def on_modified(self, event: FileModifiedEvent) -> None:  # type: ignore[override]
        if not event.is_directory and self._is_supported(event.src_path):
            logger.info("Modified file: %s", event.src_path)
            self._svc.index_file(event.src_path)

    def on_deleted(self, event: FileDeletedEvent) -> None:  # type: ignore[override]
        if not event.is_directory:
            logger.info("Deleted file: %s", event.src_path)
            self._svc.remove_file(event.src_path)

    @staticmethod
    def _is_supported(path: str) -> bool:
        return Path(path).suffix.lower() in settings.TALAASH_SUPPORTED_EXTENSIONS


class FileWatcher:
    """Watches a folder and keeps the index up-to-date automatically."""

    def __init__(self, index_service: "IndexService") -> None:
        self._svc = index_service
        self._observer: Optional[Observer] = None
        self._lock = threading.Lock()

    def start(self, folder_path: str) -> None:
        """Start the background observer thread."""
        with self._lock:
            if self._observer and self._observer.is_alive():
                logger.warning("Watcher already running")
                return
            handler = _Handler(self._svc)
            self._observer = Observer()
            self._observer.schedule(handler, folder_path, recursive=True)
            self._observer.daemon = True
            self._observer.start()
            logger.info("Watching: %s", folder_path)
            print(f"[Talaash] Watching '{folder_path}' for changes…")

    def stop(self) -> None:
        """Stop the background observer thread."""
        with self._lock:
            if self._observer:
                self._observer.stop()
                self._observer.join()
                self._observer = None
                logger.info("Watcher stopped")
                print("[Talaash] Watcher stopped.")


# ---------------------------------------------------------------------------
# Module-level convenience functions (backward compat)
# ---------------------------------------------------------------------------

_watcher: Optional[FileWatcher] = None


def start_watching(folder_path: str) -> None:
    """Backward-compat: start watching using the singleton IndexService."""
    global _watcher
    from src.services import get_services
    index_svc, _ = get_services()
    _watcher = FileWatcher(index_svc)
    _watcher.start(folder_path)


def stop_watching() -> None:
    """Backward-compat: stop the singleton watcher."""
    global _watcher
    if _watcher:
        _watcher.stop()
        _watcher = None
