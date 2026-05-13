"""IndexService — owns all file indexing business logic."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from tqdm import tqdm

from src.documents.classifier import classify_document
from src.extractor import get_extractor
from src.languages.detector import detect_language
from src.storage.database import STATUS_FAILED, STATUS_INDEXED, STATUS_PENDING
from src.utils.helpers import chunk_text, get_file_hash, get_file_size_mb
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.search.embeddings import Embedder
    from src.storage.database import Database
    from src.storage.vector_store import VectorStore

logger = get_logger(__name__)


class IndexService:
    """Orchestrates indexing: extraction → classification → embedding → storage."""

    def __init__(
        self,
        db: Database,
        vector_store: VectorStore,
        embedder: Embedder,
        max_workers: int = 4,
    ) -> None:
        self.db = db
        self.vector_store = vector_store
        self.embedder = embedder
        self.max_workers = max_workers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_folder(self, folder_path: str, recursive: bool = True) -> dict:
        """Index all supported files in a folder."""
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Not a directory: {folder_path}")

        # Re-queue any files whose indexing was interrupted in a previous run
        self._requeue_stale_pending()

        from src.utils.config import settings

        exts = set(settings.TALAASH_SUPPORTED_EXTENSIONS)
        max_mb = settings.TALAASH_MAX_FILE_SIZE_MB

        pattern = "**/*" if recursive else "*"
        candidates = [
            p
            for p in folder.glob(pattern)
            if p.is_file() and not self._should_skip(p, exts, max_mb)[0]
        ]
        logger.info("Found %d candidate files in %s", len(candidates), folder_path)

        # Pre-init storage before thread pool to avoid init races
        self.db.get_stats()
        self.vector_store.get_count()

        type_counts: defaultdict[str, int] = defaultdict(int)
        success_count = 0
        error_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._process_file, f): f for f in candidates}
            with tqdm(total=len(candidates), unit="file", desc="Indexing") as bar:
                for future in as_completed(futures):
                    try:
                        ok, _, doc_type = future.result()
                        if ok:
                            success_count += 1
                            if doc_type:
                                type_counts[doc_type] += 1
                        else:
                            error_count += 1
                    except Exception as exc:
                        logger.warning("Unexpected indexing error: %s", exc)
                        error_count += 1
                    bar.update(1)

        by_type = dict(type_counts)
        other = success_count - sum(by_type.values())
        if other > 0:
            by_type["other"] = other

        print(f"\n[Talaash] Indexed {success_count} files. Errors: {error_count}.")
        for dtype, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"  {count:>5}  {dtype}")

        return {"indexed": success_count, "errors": error_count, "by_type": by_type}

    def index_file(self, file_path: str) -> bool:
        """Index a single file. Returns True if indexing succeeded."""
        from src.utils.config import settings

        p = Path(file_path)
        skip, reason = self._should_skip(
            p, set(settings.TALAASH_SUPPORTED_EXTENSIONS), settings.TALAASH_MAX_FILE_SIZE_MB
        )
        if skip:
            logger.debug("Skipping %s: %s", file_path, reason)
            return False
        ok, _, _ = self._process_file(p)
        return ok

    def remove_file(self, file_path: str) -> None:
        """Remove a deleted file from both stores."""
        self.db.delete_file_record(file_path)
        self.vector_store.delete_file(file_path)
        logger.info("Removed from index: %s", file_path)

    def clear(self) -> None:
        """Wipe the entire index — single SQL DELETE + ChromaDB reset."""
        self.vector_store.clear()
        self.db.delete_all()
        logger.info("Index cleared")

    def get_stats(self) -> dict[str, int]:
        return self.db.get_stats()

    def get_count(self) -> int:
        return self.vector_store.get_count()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _should_skip(
        self,
        file_path: Path,
        supported_extensions: set[str],
        max_size_mb: int,
    ) -> tuple[bool, str]:
        if file_path.suffix.lower() not in supported_extensions:
            return True, "unsupported extension"
        try:
            size_mb = get_file_size_mb(file_path)
        except OSError:
            return True, "cannot stat file"
        if size_mb > max_size_mb:
            return True, f"too large ({size_mb:.1f} MB)"
        return False, ""

    def _requeue_stale_pending(self, older_than_minutes: int = 5) -> None:
        """Reset stuck 'pending' records so they get re-indexed this run."""
        stale = self.db.get_stale_pending(older_than_minutes)
        if stale:
            logger.info("Re-queuing %d stale pending files", len(stale))
            for record in stale:
                self.db.set_status(record["file_path"], STATUS_FAILED)

    def _process_file(self, file_path: Path) -> tuple[bool, str, str | None]:
        """Index one file atomically using a pending → indexed/failed status flow.

        Write order:
          1. SQLite status=pending   (crash here → re-queued on next run)
          2. ChromaDB upsert         (crash here → pending cleaned up on next run)
          3. SQLite status=indexed   (both stores consistent)
        """
        path_str = str(file_path)

        try:
            file_hash = get_file_hash(file_path)
        except OSError as exc:
            logger.warning("Cannot hash %s: %s", path_str, exc)
            return False, path_str, None

        # Skip files already successfully indexed with no content change
        existing = self.db.get_file_by_path(path_str)
        if (
            existing
            and existing.get("file_hash") == file_hash
            and existing.get("status") == STATUS_INDEXED
        ):
            logger.debug("Unchanged, skipping: %s", path_str)
            return True, path_str, existing.get("file_type")

        size_mb = get_file_size_mb(file_path)
        base_info = {
            "file_path": path_str,
            "file_name": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size_mb": round(size_mb, 4),
            "file_hash": file_hash,
            "file_type": existing.get("file_type", "unknown") if existing else "unknown",
            "language_detected": existing.get("language_detected", "en") if existing else "en",
        }

        # Step 1 — mark pending
        self.db.save_file_record({**base_info, "status": STATUS_PENDING})

        # Step 2 — extract
        extractor = get_extractor(path_str)
        if extractor is None:
            self.db.set_status(path_str, STATUS_FAILED)
            return False, path_str, None

        result = extractor.extract(path_str)
        if not result["success"] or not result["text"]:
            logger.debug("Extraction failed for %s: %s", path_str, result.get("error"))
            self.db.set_status(path_str, STATUS_FAILED)
            return False, path_str, None

        content = result["text"]
        doc_type = classify_document(content, file_path.name)
        language = detect_language(content)

        chunks = chunk_text(content, max_chars=512)
        embedding = self.embedder.encode(chunks[0] if chunks else content[:512])

        now_str = str(datetime.now(UTC))

        # Step 3 — write to ChromaDB
        self.vector_store.add_file(
            file_id=path_str,
            text=content[:32_000],
            embedding=embedding,
            metadata={
                **base_info,
                "file_type": doc_type,
                "language_detected": language,
                "last_indexed_at": now_str,
            },
        )

        # Step 4 — mark indexed in SQLite (both stores now consistent)
        self.db.save_file_record(
            {
                **base_info,
                "file_type": doc_type,
                "language_detected": language,
                "status": STATUS_INDEXED,
            }
        )

        logger.debug("Indexed %s → %s (%s)", file_path.name, doc_type, language)
        return True, path_str, doc_type
