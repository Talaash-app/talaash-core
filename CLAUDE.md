# Talaash — Core

Local, privacy-first AI-powered file search. Python backend with a CLI, REST API, and file watcher.

## Commands

```bash
# Tests
python -m pytest tests/ -v

# CLI
python main.py index --folder /path/to/docs   # index a folder
python main.py index --folder /path --watch   # index + watch for changes
python main.py                                 # interactive search REPL

# API server
python main.py server                          # starts on port 8765 (default)
```

## Module map

```
main.py                        CLI entry point — argparse, passes services down to commands
src/
  services/
    __init__.py                create_services() factory + get_services() singleton
    index_service.py           IndexService — all indexing logic
    search_service.py          SearchService — full search pipeline
  storage/
    database.py                Database (SQLite/SQLAlchemy) — IndexedFile model, status flow
    vector_store.py            VectorStore (ChromaDB) — embeddings store
  search/
    embeddings.py              Embedder (sentence-transformers, multilingual, lazy-load)
    ranking.py                 Re-ranking after vector search
  languages/
    detector.py                Language detection (en/hi/mr)
    processor.py               extract_search_intent() — strips filler words from queries
  documents/
    classifier.py              Classifies doc type (aadhaar, itr, bank_statement, etc.)
  extractor/                   Per-format text extractors (pdf, docx, image OCR, txt)
  indexer/
    watcher.py                 FileWatcher — watchdog-based live index updates
  api/
    server.py                  FastAPI app factory, uvicorn runner
    routes/index.py            POST /index, GET /index/status, DELETE /index
    routes/search.py           POST /search
    dependencies.py            FastAPI Depends providers for IndexService/SearchService
  utils/
    config.py                  Settings (pydantic-settings, TALAASH_* env vars)
tests/
  conftest.py                  Fixtures: shared_embedder (session), isolated_services (autouse)
```

## Architecture rules

**All business logic routes through the service layer — always.**
- Never import from `src.storage.*` or `src.search.*` directly in routes, CLI, or watcher.
- Use `create_services(settings)` to build services; use `get_services()` for the production singleton.
- `IndexService` and `SearchService` are the only two public surfaces for callers.

**Dependency injection, not globals.**
- No module-level singletons outside `services/__init__.py`.
- API routes use `Depends(get_index_service)` / `Depends(get_search_service)`.
- Tests pass a `Settings(TALAASH_DB_PATH=..., TALAASH_INDEX_PATH=...)` directly to `create_services()`.

**Atomic indexing — the status flow in `_process_file` must be preserved:**
1. SQLite `status=pending`
2. Extract → embed → ChromaDB upsert
3. SQLite `status=indexed`
Never skip steps or collapse them.

## Testing rules

- Tests use the `isolated_services` autouse fixture — it creates a fresh tmp-dir-backed service pair per test. Never monkeypatch storage singletons manually.
- The `shared_embedder` fixture (session scope) loads the model once per run. Never create an `Embedder` inside a test directly — use the fixture.
- Run `python -m pytest tests/ -v` to verify. All 19 tests must pass before merging.

## Config

All settings live in `src/utils/config.py` as `TALAASH_*` env vars. Key ones:
- `TALAASH_DB_PATH` — SQLite directory
- `TALAASH_INDEX_PATH` — ChromaDB directory
- `TALAASH_MODEL_NAME` — sentence-transformers model (default: `paraphrase-multilingual-MiniLM-L12-v2`)
- `TALAASH_SUPPORTED_EXTENSIONS` — list of indexable file extensions
- `TALAASH_API_PORT` — REST API port (default: 8765)

## Code conventions

- No comments unless the WHY is non-obvious.
- No docstrings on obvious methods.
- No `Optional[X]` — use `X | None` (Python 3.10+ style).
- Linter: `ruff` (line length 100, rules E/F/I/UP).

## Phase status

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Service Layer | Done |
| 2 | Atomic Indexing + Intent + Memory | Done |
| 3 | Config + Testability | Done |
| 4 | CLI Cleanup | Next |
| 5 | Full Test Rewrite | Pending |

Phase docs: `../docs/phases/`
