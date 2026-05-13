"""Tests for language detection."""

from __future__ import annotations


class TestLanguageDetector:
    """Tests for src.languages.detector.detect_language."""

    def test_english_detected(self) -> None:
        """Clear English text must be detected as 'en'."""
        from src.languages.detector import detect_language

        lang = detect_language(
            "This is an income tax return document filed for the assessment year 2023."
        )
        assert lang == "en"

    def test_hindi_detected(self) -> None:
        """Clear Hindi text must be detected as 'hi'."""
        from src.languages.detector import detect_language

        lang = detect_language(
            "यह एक आधार कार्ड की जानकारी है जो UIDAI द्वारा जारी की गई है।"
            " इसमें आपकी विशिष्ट पहचान संख्या होती है।"
        )
        assert lang == "hi"

    def test_marathi_detected(self) -> None:
        """Clear Marathi text should be detected (hi or mr — both acceptable)."""
        from src.languages.detector import detect_language

        lang = detect_language(
            "हे माझ्या बँक स्टेटमेंटचे नमुना आहे. व्यवहाराची माहिती येथे आहे. शिल्लक रक्कम आणि जमा रक्कम दर्शविली आहे."
        )
        # langdetect sometimes misclassifies Marathi as Hindi; both are acceptable
        assert lang in ("mr", "hi")

    def test_very_short_text_defaults_to_english(self) -> None:
        """Very short text (below threshold) must default to 'en'."""
        from src.languages.detector import detect_language

        lang = detect_language("Hi")
        assert lang == "en"

    def test_empty_string_defaults_to_english(self) -> None:
        """Empty string must return 'en' without raising."""
        from src.languages.detector import detect_language

        lang = detect_language("")
        assert lang == "en"
