"""NLLB FLORES-200 Language Code Utilities adhering to Document 10."""

import logging

from packages.language_registry import normalize_code

logger = logging.getLogger(__name__)

# ISO-639-3 -> NLLB FLORES-200 language code mapping
_ISO639_3_TO_NLLB: dict[str, str] = {
    "eng": "eng_Latn",
    "spa": "spa_Latn",
    "fra": "fra_Latn",
    "deu": "deu_Latn",
    "zho": "zho_Hans",
    "jpn": "jpn_Jpan",
    "hin": "hin_Deva",
    "por": "por_Latn",
    "ara": "ara_Arab",
    "rus": "rus_Cyrl",
    "ita": "ita_Latn",
    "kor": "kor_Hang",
    "tur": "tur_Latn",
    "nld": "nld_Latn",
    "pol": "pol_Latn",
    "swe": "swe_Latn",
    "vie": "vie_Latn",
    "ind": "ind_Latn",
}

# Invert mapping: FLORES-200 -> ISO-639-3
_NLLB_TO_ISO639_3: dict[str, str] = {v: k for k, v in _ISO639_3_TO_NLLB.items()}


def iso639_3_to_nllb(code: str) -> str:
    """Converts a 3-letter ISO-639-3 code to an NLLB FLORES-200 language tag."""
    cleaned = normalize_code(code)
    if cleaned in _ISO639_3_TO_NLLB:
        return _ISO639_3_TO_NLLB[cleaned]

    # If code already looks like an NLLB tag (e.g. 'eng_Latn')
    if cleaned in _NLLB_TO_ISO639_3:
        return cleaned

    logger.warning("Unmapped NLLB language code '%s', defaulting to 'eng_Latn'", code)
    return "eng_Latn"


def nllb_to_iso639_3(nllb_tag: str) -> str:
    """Converts an NLLB FLORES-200 language tag to an ISO-639-3 3-letter code."""
    cleaned = nllb_tag.strip()
    if cleaned in _NLLB_TO_ISO639_3:
        return _NLLB_TO_ISO639_3[cleaned]

    # Fallback to the first 3 characters if length >= 3
    prefix = cleaned.split("_")[0].lower()
    if prefix in _ISO639_3_TO_NLLB:
        return prefix

    return "eng"
