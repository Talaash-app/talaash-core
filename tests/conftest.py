"""Pytest fixtures for Talaash tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.search.embeddings import Embedder
from src.services import create_services
from src.utils.config import Settings

# ---------------------------------------------------------------------------
# Shared embedder — loaded once per test session to avoid re-downloading
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def shared_embedder() -> Embedder:
    from src.utils.config import settings
    embedder = Embedder(settings.TALAASH_MODEL_NAME, settings.TALAASH_BATCH_SIZE)
    embedder.load()
    return embedder


# ---------------------------------------------------------------------------
# Storage isolation — each test gets its own tmp-dir-backed services
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_services(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shared_embedder: Embedder) -> None:
    import src.services as svc_mod
    index_svc, search_svc = create_services(
        Settings(TALAASH_DB_PATH=str(tmp_path / "db"), TALAASH_INDEX_PATH=str(tmp_path / "idx")),
        embedder=shared_embedder,
    )
    monkeypatch.setattr(svc_mod, "_index_svc", index_svc)
    monkeypatch.setattr(svc_mod, "_search_svc", search_svc)


# ---------------------------------------------------------------------------
# File fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def temp_folder(tmp_path: Path) -> Path:
    """Return a temporary directory pre-populated with sample text files."""
    (tmp_path / "sample.txt").write_text(
        "This is a sample bank statement. Transactions for account 1234.",
        encoding="utf-8",
    )
    (tmp_path / "hindi.txt").write_text(
        "यह एक आधार कार्ड की जानकारी है। UIDAI द्वारा जारी।",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal valid PDF with embedded text and return its path."""
    try:
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (72, 72),
            "Income Tax Return — Assessment Year 2023-24\nGross Total Income: 500000",
        )
        pdf_path = tmp_path / "sample.pdf"
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path
    except Exception:
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/Resources<<>>/MediaBox[0 0 612 792]"
            b"/Contents 4 0 R>>endobj\n"
            b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (ITR Document) Tj ET\n"
            b"endstream\nendobj\n"
            b"xref\n0 5\n0000000000 65535 f \n"
            b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n9\n%%EOF"
        )
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(pdf_bytes)
        return pdf_path


@pytest.fixture()
def sample_image(tmp_path: Path) -> Path:
    """Create a small white PNG image and return its path."""
    try:
        from PIL import Image

        img = Image.new("RGB", (200, 100), color="white")
        img_path = tmp_path / "sample.png"
        img.save(str(img_path))
        return img_path
    except ImportError:
        img_path = tmp_path / "sample.png"
        png_bytes = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,
            0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82,
        ])
        img_path.write_bytes(png_bytes)
        return img_path
