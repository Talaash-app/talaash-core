"""Image text extractor using Tesseract OCR."""

from __future__ import annotations

from typing import Any

from src.extractor.base import BaseExtractor
from src.utils.helpers import clean_text
from src.utils.logger import get_logger

logger = get_logger(__name__)

TESSERACT_LANG = "eng+hin+mar"


class ImageExtractor(BaseExtractor):
    """Extract text from image files via Tesseract OCR with preprocessing."""

    def extract(self, file_path: str) -> dict[str, Any]:
        """Extract text from an image using Tesseract after Pillow preprocessing.

        Converts the image to grayscale and enhances contrast to improve OCR
        accuracy, especially for scanned documents.
        """
        try:
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter
        except ImportError:
            return self._fail("pytesseract and/or Pillow not installed")

        try:
            img = Image.open(file_path)
        except Exception as exc:
            return self._fail(f"Cannot open image: {exc}")

        try:
            img = img.convert("L")  # Grayscale
            img = img.filter(ImageFilter.SHARPEN)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)

            text = pytesseract.image_to_string(img, lang=TESSERACT_LANG)
            metadata = {
                "width": img.width,
                "height": img.height,
                "format": getattr(img, "format", "unknown"),
            }
            return self._ok(clean_text(text), metadata)

        except pytesseract.TesseractNotFoundError:
            return self._fail("Tesseract is not installed or not in PATH")
        except Exception as exc:
            logger.warning("Image OCR failed for %s: %s", file_path, exc)
            return self._fail(str(exc))
