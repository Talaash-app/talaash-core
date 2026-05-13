"""SQLite metadata store — Database class with proper session lifecycle."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    delete,
    func,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Valid values for IndexedFile.status
STATUS_PENDING = "pending"
STATUS_INDEXED = "indexed"
STATUS_FAILED  = "failed"


class Base(DeclarativeBase):
    pass


class IndexedFile(Base):
    __tablename__ = "indexed_files"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    file_path         = Column(String, unique=True, nullable=False, index=True)
    file_name         = Column(String, nullable=False)
    file_extension    = Column(String, nullable=False)
    file_size_mb      = Column(Float,  nullable=False)
    file_hash         = Column(String, nullable=False, index=True)
    file_type         = Column(String, default="unknown")
    language_detected = Column(String, default="en")
    status            = Column(String, default=STATUS_INDEXED, index=True)
    last_indexed_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at        = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Database:
    """SQLite metadata store for indexed files.

    Each instance owns its engine and session factory — fully injectable,
    no module-level globals required.
    """

    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{path / 'src.db'}", echo=False)
        Base.metadata.create_all(self._engine)
        self._migrate()
        self._Session = sessionmaker(bind=self._engine)
        logger.debug("Database ready at %s", path)

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Commit on success, rollback on error, always close."""
        s = self._Session()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save_file_record(self, file_info: dict) -> None:
        """Insert or update a file record."""
        now = datetime.now(timezone.utc)
        with self.session() as s:
            existing = s.execute(
                select(IndexedFile).where(IndexedFile.file_path == file_info["file_path"])
            ).scalar_one_or_none()

            if existing:
                for key, value in file_info.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.last_indexed_at = now
            else:
                s.add(IndexedFile(
                    file_path         = file_info["file_path"],
                    file_name         = file_info["file_name"],
                    file_extension    = file_info["file_extension"],
                    file_size_mb      = file_info["file_size_mb"],
                    file_hash         = file_info["file_hash"],
                    file_type         = file_info.get("file_type", "unknown"),
                    language_detected = file_info.get("language_detected", "en"),
                    status            = file_info.get("status", STATUS_INDEXED),
                    last_indexed_at   = now,
                    created_at        = now,
                ))

    def set_status(self, path: str, status: str) -> None:
        """Update only the status field for a given file path."""
        with self.session() as s:
            row = s.execute(
                select(IndexedFile).where(IndexedFile.file_path == path)
            ).scalar_one_or_none()
            if row:
                row.status = status
                row.last_indexed_at = datetime.now(timezone.utc)

    def delete_file_record(self, path: str) -> None:
        """Remove the record for a path if it exists."""
        with self.session() as s:
            row = s.execute(
                select(IndexedFile).where(IndexedFile.file_path == path)
            ).scalar_one_or_none()
            if row:
                s.delete(row)

    def delete_all(self) -> None:
        """Delete every record in a single SQL statement."""
        with self.session() as s:
            s.execute(delete(IndexedFile))
        logger.info("All file records deleted")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_file_by_path(self, path: str) -> Optional[dict]:
        with self.session() as s:
            row = s.execute(
                select(IndexedFile).where(IndexedFile.file_path == path)
            ).scalar_one_or_none()
            return _row_to_dict(row) if row else None

    def get_file_by_hash(self, file_hash: str) -> Optional[dict]:
        with self.session() as s:
            row = s.execute(
                select(IndexedFile).where(IndexedFile.file_hash == file_hash)
            ).scalar_one_or_none()
            return _row_to_dict(row) if row else None

    def count(self) -> int:
        """Total number of successfully indexed files."""
        with self.session() as s:
            return s.execute(
                select(func.count(IndexedFile.id)).where(
                    IndexedFile.status == STATUS_INDEXED
                )
            ).scalar_one()

    def get_stale_pending(self, older_than_minutes: int = 5) -> list[dict]:
        """Return pending records stuck for longer than older_than_minutes.

        These are files whose indexing was interrupted (process killed, crash).
        The caller should re-queue them.
        """
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
        with self.session() as s:
            rows = s.execute(
                select(IndexedFile).where(
                    IndexedFile.status == STATUS_PENDING,
                    IndexedFile.last_indexed_at < cutoff,
                )
            ).scalars().all()
            return [_row_to_dict(r) for r in rows]

    def get_all_indexed_files(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """Return indexed file records with optional pagination."""
        with self.session() as s:
            q = select(IndexedFile).where(IndexedFile.status == STATUS_INDEXED)
            if offset:
                q = q.offset(offset)
            if limit is not None:
                q = q.limit(limit)
            rows = s.execute(q).scalars().all()
            return [_row_to_dict(r) for r in rows]

    def get_stats(self) -> dict[str, int]:
        """Count of successfully indexed files grouped by file_type."""
        with self.session() as s:
            rows = s.execute(
                select(
                    IndexedFile.file_type,
                    func.count(IndexedFile.id).label("count"),
                )
                .where(IndexedFile.status == STATUS_INDEXED)
                .group_by(IndexedFile.file_type)
            ).all()
            return {row.file_type: row.count for row in rows}

    # ------------------------------------------------------------------
    # Schema migration
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        """Add columns introduced after the initial schema without losing data."""
        with self._engine.connect() as conn:
            existing_cols = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(indexed_files)"))
            }
            if "status" not in existing_cols:
                # Default existing rows to 'indexed' — they were indexed successfully
                conn.execute(text(
                    f"ALTER TABLE indexed_files "
                    f"ADD COLUMN status VARCHAR DEFAULT '{STATUS_INDEXED}'"
                ))
                conn.commit()
                logger.info("Migrated: added 'status' column to indexed_files")


def _row_to_dict(row: IndexedFile) -> dict:
    return {
        "id":                row.id,
        "file_path":         row.file_path,
        "file_name":         row.file_name,
        "file_extension":    row.file_extension,
        "file_size_mb":      row.file_size_mb,
        "file_hash":         row.file_hash,
        "file_type":         row.file_type,
        "language_detected": row.language_detected,
        "status":            row.status,
        "last_indexed_at":   row.last_indexed_at,
        "created_at":        row.created_at,
    }

