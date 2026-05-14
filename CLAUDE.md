# CLAUDE.md — Talaash Core

## What This Is
Talaash is a 100% local, privacy-first AI file search engine.
Users find files by describing content in plain English, Hindi, or Marathi.
No cloud. No account. No data leaves the device. Ever.

Primary market: Indian Android + Windows users with messy file systems,
UUID-named government PDFs (Aadhaar, PAN, ITR), WhatsApp downloads.

---

## Non-Negotiable Constraints

- Everything runs locally. Never add any external API call that sends file content or queries to a remote server.
- Never import or suggest cloud storage, OpenAI API, or any hosted LLM.
- All AI inference uses local models only (sentence-transformers, Ollama, Tesseract).
- Do not add features not explicitly requested. Ask first.
- Never crash on a single bad file. Wrap all file I/O in try/except. Log and continue.

---

## Tech Stack — Fixed Decisions

Do not suggest alternatives to these. They are decided.

| Concern | Library | Notes |
|---|---|---|
| PDF extraction | PyMuPDF (fitz) | Fast, handles encrypted gracefully |
| OCR fallback | pytesseract + Pillow | eng+hin+mar lang packs |
| Embeddings | sentence-transformers | Model: paraphrase-multilingual-MiniLM-L12-v2 |
| Vector store | FAISS (faiss-cpu) | Local index, no server needed |
| Metadata DB | SQLite via SQLAlchemy | One .db file, no migrations framework |
| API layer | FastAPI + uvicorn | Port 8765, localhost only |
| Word docs | python-docx | — |
| Language detect | langdetect | Fallback: assume "en" |
| File watching | watchdog | Background thread |
| Config | pydantic-settings | Reads from .env |
| Logging | Python stdlib logging | Structured, file + console |
| CLI | argparse | Already wired in main.py |
| Progress | tqdm | Indexing progress bar only |
| Code style | ruff | Config in pyproject.toml |

---

## Architecture — How Data Flows

### Indexing
```
File on disk
  → extractor/ (raw text + metadata)
  → languages/detector.py (language tag)
  → documents/classifier.py (doc type: aadhaar, pan, etc.)
  → search/embeddings.py (float[] vector)
  → storage/database.py (SQLite row: path, hash, type, lang, timestamp)
  → storage/vector_store.py (FAISS upsert)
```

### Searching
```
User query string
  → languages/detector.py (query language)
  → languages/processor.py (normalize for that language)
  → search/embeddings.py (query vector)
  → storage/vector_store.py (top-N FAISS lookup)
  → storage/database.py (enrich with metadata)
  → search/ranking.py (re-rank by doc type boost, recency, score)
  → List[SearchResult] returned to caller
```

### API Layer
```
HTTP POST /search  →  api/routes/search.py  →  services/search_service.py
HTTP POST /index   →  api/routes/index.py   →  services/index_service.py
HTTP GET  /health  →  api/routes/health.py  →  (direct, no service needed)
```

The API layer does zero business logic. It validates input (Pydantic),
calls the service, and serializes output. Nothing else.

---

## Folder Rules — What Goes Where

```
src/api/          HTTP concerns only. No file I/O. No ML. No SQL.
src/services/     Orchestration only. Calls extractor, embeddings, storage.
                  No direct file I/O. No SQL queries. No HTTP.
src/extractor/    File I/O only. Returns plain text + metadata dict.
                  No embeddings. No DB writes.
src/search/       ML only. Embeddings and ranking math.
                  No file I/O. No DB writes. No HTTP.
src/storage/      DB and vector index only. No business logic.
src/languages/    Text normalization only. No file I/O. No DB.
src/documents/    Pattern matching only. No file I/O. No DB. No ML.
src/utils/        Shared primitives. No imports from src/ siblings.
```

If logic does not fit cleanly into one folder, split it before mixing concerns.

---

## Key Patterns — Always Follow These

### Extractor return shape
Every extractor returns this exact dict. No exceptions.
```python
{
    "text": str,          # extracted content, empty string if none
    "metadata": dict,     # title, author, page_count, etc. — optional keys
    "success": bool,
    "error": str | None   # None on success, message on failure
}
```

### SearchResult shape
```python
{
    "file_name": str,
    "file_path": str,
    "file_type": str,       # "aadhaar", "pan", "bank_statement", "unknown", etc.
    "language": str,        # "en", "hi", "mr", etc.
    "preview": str,         # first 200 chars of matched text
    "relevance_score": float,  # 0.0 – 1.0
    "last_modified": str    # ISO 8601
}
```

### Error handling rule
```python
# CORRECT
try:
    text = extract_pdf(path)
except Exception as e:
    logger.error("Failed to extract %s: %s", path, e)
    return {"text": "", "metadata": {}, "success": False, "error": str(e)}

# WRONG — never do this
text = extract_pdf(path)  # unguarded
```

### Config access rule
```python
# CORRECT — always import the singleton
from src.utils.config import settings
port = settings.api_port

# WRONG — never hardcode
port = 8765
```

### Logging rule
```python
# CORRECT
logger.info("Indexed %d files, skipped %d", indexed, skipped)

# WRONG
print(f"Indexed {indexed} files")
```

---

## SQLite Schema — Do Not Change Without Asking

```sql
CREATE TABLE indexed_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path       TEXT UNIQUE NOT NULL,
    file_name       TEXT NOT NULL,
    file_extension  TEXT NOT NULL,
    file_size_mb    REAL,
    file_hash       TEXT NOT NULL,        -- MD5, used to skip unchanged files
    file_type       TEXT DEFAULT 'unknown',
    language        TEXT DEFAULT 'en',
    last_indexed_at TEXT NOT NULL,        -- ISO 8601
    created_at      TEXT NOT NULL         -- ISO 8601
);
```

---

## Embedding Model — Critical Notes

Model: `paraphrase-multilingual-MiniLM-L12-v2`
- ~470MB download on first run. Show a user-friendly message, not a silent hang.
- Load ONCE at startup into a module-level singleton. Never reload per request.
- Supports 50+ languages including Hindi (hi) and Marathi (mr) natively.
- encode() input: plain string. Output: numpy float32 array → cast to list for FAISS.

```python
# CORRECT — singleton pattern
_model = None

def get_model():
    global _model
    if _model is None:
        logger.info("Loading embedding model (first run may take 30s)...")
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model
```

---

## Indian Document Classifier — Patterns

Classifier checks extracted text for these keywords.
Both English and Devanagari variants must be checked.
Returns the FIRST match. Order matters — more specific first.

```
aadhaar_card    : ["aadhaar", "uid", "uidai", "आधार", "unique identification"]
pan_card        : ["permanent account number", "income tax dept", "PAN", "पैन"]
passport        : ["passport", "republic of india", "पासपोर्ट"]
voter_id        : ["election commission", "electors photo", "मतदाता"]
driving_license : ["driving licence", "motor vehicles", "ड्राइविंग लाइसेंस"]
bank_statement  : ["statement of account", "account number", "ifsc", "बैंक स्टेटमेंट"]
salary_slip     : ["salary slip", "payslip", "basic pay", "वेतन पर्ची"]
itr             : ["income tax return", "ITR-", "assessment year", "आयकर विवरणी"]
form_16         : ["form 16", "tds certificate", "26as"]
marksheet       : ["mark sheet", "result", "university", "अंकपत्र", "board of"]
insurance       : ["insurance", "policy number", "premium", "बीमा पॉलिसी"]
rental_agreement: ["rent agreement", "lease deed", "tenant", "किराया"]
```

---

## FAISS Index Notes

- Index file: `{settings.index_path}/talaash.index`
- ID mapping file: `{settings.index_path}/talaash_ids.json`
  Maps FAISS internal int IDs → file_path strings
- Use `faiss.IndexFlatIP` (inner product = cosine after normalization)
- Normalize all vectors before add/search with `faiss.normalize_L2()`
- Rebuild index from SQLite if .index file is missing or corrupt

```python
# CORRECT search flow
query_vec = np.array([embedding], dtype=np.float32)
faiss.normalize_L2(query_vec)
distances, indices = index.search(query_vec, k=n_results)
```

---

## File Watcher Behaviour

- Watch configured folders recursively
- On CREATE or MODIFY: call index_service.index_file(path)
- On DELETE: call storage.database.delete_file_record(path) + remove from FAISS
- Skip files larger than settings.max_file_size_mb
- Skip file extensions not in settings.supported_extensions
- Debounce MODIFY events: wait 2 seconds before indexing (handles partial writes)
- Run in daemon thread so it exits when main process exits

---

## CLI Commands (main.py)

```
python main.py index --folder /path          Index folder once
python main.py index --folder /path --watch  Index then watch for changes
python main.py search "query text"           One-shot search, print results
python main.py server                        Start FastAPI on port 8765
python main.py stats                         Print index statistics
python main.py clear                         Wipe index and database
```

---

## Environment Variables (.env)

```
TALAASH_DB_PATH=./talaash_db/talaash.db
TALAASH_INDEX_PATH=./talaash_index
TALAASH_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
TALAASH_MAX_FILE_SIZE_MB=100
TALAASH_SUPPORTED_EXTENSIONS=.pdf,.docx,.txt,.png,.jpg,.jpeg
TALAASH_BATCH_SIZE=16
TALAASH_API_PORT=8765
TALAASH_API_HOST=127.0.0.1
TALAASH_LOG_LEVEL=INFO
TALAASH_LOG_FILE=talaash.log
TALAASH_WATCH_DEBOUNCE_SECONDS=2
```

All settings accessed via `from src.utils.config import settings`.

---

## OCR Rules

1. Try PyMuPDF text extraction first.
2. If `len(text.strip()) < 50` → assume scanned → fall back to Tesseract.
3. Tesseract lang string: `eng+hin+mar`
4. Preprocess image before OCR: grayscale → contrast enhance → 300 DPI.
5. OCR is slow (~3–8s per page). Log a debug message per page.
6. Never crash on OCR failure. Return empty text with success=False.

---

## What Is Not Built Yet

Do not generate code for these without being asked:
- Desktop UI (Tauri) — lives in talaash-desktop/ repo, not here
- Mobile app (Flutter) — lives in talaash-mobile/ repo, not here
- PC ↔ Phone sync — future feature
- Cloud backup — will never exist (privacy-first)
- User accounts / authentication — will never exist
- WhatsApp chat indexing — planned, not started
- Audio transcription (Whisper) — planned, not started

---

## Code Quality Rules

- Every function has a docstring (one line minimum).
- Every function has full type hints (parameters + return type).
- Max function length: 40 lines. Split if longer.
- Max file length: 200 lines. Split if longer.
- No hardcoded strings except in indian_docs.py patterns.
- No print() statements. Use logger exclusively.
- No TODOs left in committed code.
- Run `ruff check . && ruff format .` before every commit.

---

## Testing Rules

- Tests live in tests/. Mirror the src/ structure.
- Use pytest fixtures from conftest.py. Never create real files in tests.
- All tests must pass with `pytest tests/ -v`.
- Use tmp_path fixture for any file system operations.
- Mock external calls (watchdog events, etc.) with pytest-mock.
- Target: every public function in src/ has at least one test.

---
