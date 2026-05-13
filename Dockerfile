# ── Talaash — core Python service ──────────────────────────────────────────
#
# Build:  docker build -t talaash ./core
# Run:    docker-compose up          (API server)
#         docker-compose run --rm api index --folder /documents
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

# ---------------------------------------------------------------------------
# 1. System dependencies
#    - tesseract-ocr      : OCR engine for scanned PDFs and images
#    - tesseract-ocr-hin  : Hindi language pack
#    - tesseract-ocr-mar  : Marathi language pack
#    - libgomp1           : OpenMP — required by PyTorch for CPU parallelism
#    - libglib2.0-0       : GLib — pulled in by several Python native libs
#    - libgl1             : OpenGL stub — needed by PyMuPDF on headless Linux
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-hin \
        tesseract-ocr-mar \
        libgomp1 \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# 2. Non-root user
#    Running as root inside a container is a security anti-pattern.
# ---------------------------------------------------------------------------
RUN useradd -m -u 1000 talaash

WORKDIR /app

# ---------------------------------------------------------------------------
# 3. Python dependencies
#    Install CPU-only PyTorch first (the default Linux wheel pulls CUDA
#    and adds ~2 GB with no benefit for this use case).
#    sentence-transformers will detect torch is already satisfied and skip
#    reinstalling it when requirements.txt is processed next.
# ---------------------------------------------------------------------------
RUN pip install --no-cache-dir \
        torch \
        --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# 4. Application code
# ---------------------------------------------------------------------------
COPY . .
RUN pip install --no-cache-dir -e .

# ---------------------------------------------------------------------------
# 5. Data directories owned by the app user
#    /data/db     → SQLite metadata (mounted as named volume)
#    /data/index  → ChromaDB vectors (mounted as named volume)
#    /documents   → user's files mounted read-only for indexing
# ---------------------------------------------------------------------------
RUN mkdir -p /data/db /data/index /documents \
    && chown -R talaash:talaash /app /data /documents

USER talaash

# ---------------------------------------------------------------------------
# 6. Runtime environment
#    HF_HOME points the HuggingFace model cache to a predictable path
#    inside the container so it can be mounted as a named volume.
#    The model is NOT baked into the image — it downloads on first run
#    and is then persisted in the hf-cache volume.
# ---------------------------------------------------------------------------
ENV TALAASH_DB_PATH=/data/db \
    TALAASH_INDEX_PATH=/data/index \
    TALAASH_API_PORT=8765 \
    TALAASH_LOG_LEVEL=INFO \
    HF_HOME=/home/talaash/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')" \
    || exit 1

# Default: start the REST API server.
# Override CMD to run the indexer:
#   docker-compose run --rm api index --folder /documents
ENTRYPOINT ["python", "main.py"]
CMD ["server"]
