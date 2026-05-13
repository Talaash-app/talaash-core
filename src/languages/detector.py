"""Language detection using langdetect."""

from __future__ import annotations

from src.utils.logger import get_logger

logger = get_logger(__name__)

_MIN_CHARS_FOR_DETECTION = 20
_DEFAULT_LANGUAGE = "en"


def detect_language(text: str) -> str:
    """Detect the language of the given text and return its ISO 639-1 code.

    Args:
        text: The text to analyse.

    Returns:
        Language code string (e.g. "en", "hi", "mr"). Defaults to "en" if the
        text is too short or detection fails.
    """
    if not text or len(text.strip()) < _MIN_CHARS_FOR_DETECTION:
        return _DEFAULT_LANGUAGE

    try:
        from langdetect import detect, LangDetectException

        lang = detect(text[:2000])
        logger.debug("Detected language: %s", lang)
        return lang
    except Exception as exc:
        logger.debug("Language detection failed: %s", exc)
        return _DEFAULT_LANGUAGE
