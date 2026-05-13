"""PDF text extractor using PyMuPDF with Tesseract OCR fallback."""

from __future__ import annotations

import io
from typing import Any

from src.extractor.base import BaseExtractor
from src.utils.helpers import clean_text
from src.utils.logger import get_logger

logger = get_logger(__name__)

OCR_MIN_CHARS = 50
TESSERACT_LANG = "eng+hin+mar"


class PDFExtractor(BaseExtractor):
    """Extract text from PDF files using PyMuPDF, falling back to OCR."""

    def extract(self, file_path: str) -> dict[str, Any]:
        """Extract text and metadata from a PDF file.

        Tries PyMuPDF direct text extraction first. If the result has fewer
        than OCR_MIN_CHARS characters (scanned / image PDF), each page is
        rendered and fed to Tesseract for OCR.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return self._fail("PyMuPDF (fitz) is not installed")

        doc = None
        try:
            doc = fitz.open(file_path)
        except fitz.FileDataError as exc:
            return self._fail(f"Corrupted PDF: {exc}")
        except Exception as exc:
            return self._fail(f"Cannot open PDF: {exc}")

        try:
            # Handle password-protected PDFs
            if doc.needs_pass:
                return self._fail("PDF is password protected")

            metadata = self._extract_metadata(doc)
            direct_text = self._extract_direct_text(doc)

            if len(direct_text.strip()) >= OCR_MIN_CHARS:
                logger.debug("PDF direct extraction OK for %s", file_path)
                return self._ok(clean_text(direct_text), metadata)

            logger.debug(
                "PDF direct text too short (%d chars), falling back to OCR: %s",
                len(direct_text.strip()),
                file_path,
            )
            ocr_text = self._extract_ocr(doc)
            combined = (direct_text + "\n" + ocr_text).strip()
            return self._ok(clean_text(combined), metadata)

        except Exception as exc:
            logger.warning("Error extracting PDF %s: %s", file_path, exc)
            return self._fail(str(exc))
        finally:
            if doc:
                doc.close()

    def _extract_metadata(self, doc: Any) -> dict[str, Any]:
        """Pull title, author, and creation date from PDF metadata."""
        raw = doc.metadata or {}
        return {
            "title": raw.get("title", ""),
            "author": raw.get("author", ""),
            "created": raw.get("creationDate", ""),
            "page_count": doc.page_count,
        }

    def _extract_direct_text(self, doc: Any) -> str:
        """Concatenate text extracted by PyMuPDF across all pages."""
        pages: list[str] = []
        for page in doc:
            try:
                pages.append(page.get_text())
            except Exception:
                pages.append("")
        return "\n".join(pages)

    def _extract_ocr(self, doc: Any) -> str:
        """Render each page to an image and run Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return ""

        pages: list[str] = []
        for page in doc:
            try:
                # Render at 2x resolution for better OCR accuracy
                mat = __import__("fitz").Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes)).convert("L")
                text = pytesseract.image_to_string(img, lang=TESSERACT_LANG)
                pages.append(text)
            except Exception as exc:
                logger.debug("OCR failed on page: %s", exc)
                pages.append("")
        return "\n".join(pages)
