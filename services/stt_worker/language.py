"""Language code normalization utilities between Whisper and ISO-639-3 catalog."""

import logging

from packages.language_registry import SUPPORTED_LANGUAGES, normalize_code

logger = logging.getLogger(__name__)


def get_supported_languages() -> list[str]:
    """Return list of all cataloged ISO-639-3 language codes."""
    return list(SUPPORTED_LANGUAGES.keys())


# Static map for 2-letter ISO-639-1 -> 3-letter ISO-639-3
_ISO639_1_TO_3: dict[str, str] = {
    "en": "eng",
    "es": "spa",
    "fr": "fra",
    "de": "deu",
    "zh": "zho",
    "ja": "jpn",
    "hi": "hin",
    "pt": "por",
    "ar": "ara",
    "ru": "rus",
    "it": "ita",
    "ko": "kor",
    "tr": "tur",
    "nl": "nld",
    "pl": "pol",
    "sv": "swe",
    "vi": "vie",
    "id": "ind",
}

# Invert mapping for 3-letter -> 2-letter
_ISO639_3_TO_1: dict[str, str] = {v: k for k, v in _ISO639_1_TO_3.items()}

# Dynamically populate from SUPPORTED_LANGUAGES bcp47 tags
for lang_code, meta in SUPPORTED_LANGUAGES.items():
    prefix = meta.bcp47.split("-")[0].lower()
    if prefix not in _ISO639_1_TO_3:
        _ISO639_1_TO_3[prefix] = lang_code
    if lang_code not in _ISO639_3_TO_1:
        _ISO639_3_TO_1[lang_code] = prefix


def to_iso639_3(code: str) -> str:
    """Normalizes an arbitrary language tag (e.g. 'en', 'en-US', 'eng') to ISO-639-3."""
    cleaned = normalize_code(code)
    # If already 3 letters and recognized, return
    if len(cleaned) == 3 and cleaned in SUPPORTED_LANGUAGES:
        return cleaned

    # Check 2-letter prefix (from 'en' or 'en-us')
    prefix = cleaned.split("-")[0]
    if prefix in _ISO639_1_TO_3:
        return _ISO639_1_TO_3[prefix]

    # Check if 3-letter code matches static table
    if cleaned in _ISO639_1_TO_3.values():
        return cleaned

    logger.warning("Unmapped language code '%s', falling back to 'eng'", code)
    return "eng"


def to_iso639_1(code: str) -> str:
    """Converts an ISO-639-3 language code (e.g. 'eng', 'spa') to Whisper 2-letter format."""
    cleaned = normalize_code(code)
    if cleaned in _ISO639_3_TO_1:
        return _ISO639_3_TO_1[cleaned]

    # If it's already 2 letters
    if len(cleaned) == 2:
        return cleaned

    # Fallback to English
    return "en"
