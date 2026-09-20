"""Language Registry and Multi-Tier Classification Matrix (Documents 10 & 12)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class LanguageTier(StrEnum):
    TIER_1 = "TIER_1"  # Ultra-low-latency bidirectional streaming (<500ms TTFT)
    TIER_2 = "TIER_2"  # Standard real-time streaming (<1200ms TTFT)
    TIER_3 = "TIER_3"  # Batch or asynchronous fallback only


class LanguageMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str  # ISO-639-3 (e.g. 'eng', 'spa', 'hin')
    bcp47: str  # BCP-47 tag (e.g. 'en-US', 'es-ES', 'hi-IN')
    name_en: str  # English Name
    name_native: str  # Native Name
    tier: LanguageTier
    supports_stt: bool = True
    supports_nmt: bool = True
    supports_tts: bool = True
    supports_voice_clone: bool = True


SUPPORTED_LANGUAGES: dict[str, LanguageMetadata] = {
    # --- Tier 1: Ultra-low latency streaming (<500ms TTFT) ---
    "eng": LanguageMetadata(
        code="eng",
        bcp47="en-US",
        name_en="English",
        name_native="English",
        tier=LanguageTier.TIER_1,
    ),
    "spa": LanguageMetadata(
        code="spa",
        bcp47="es-ES",
        name_en="Spanish",
        name_native="Español",
        tier=LanguageTier.TIER_1,
    ),
    "fra": LanguageMetadata(
        code="fra",
        bcp47="fr-FR",
        name_en="French",
        name_native="Français",
        tier=LanguageTier.TIER_1,
    ),
    "deu": LanguageMetadata(
        code="deu",
        bcp47="de-DE",
        name_en="German",
        name_native="Deutsch",
        tier=LanguageTier.TIER_1,
    ),
    "zho": LanguageMetadata(
        code="zho",
        bcp47="zh-CN",
        name_en="Mandarin Chinese",
        name_native="中文",
        tier=LanguageTier.TIER_1,
    ),
    "jpn": LanguageMetadata(
        code="jpn",
        bcp47="ja-JP",
        name_en="Japanese",
        name_native="日本語",
        tier=LanguageTier.TIER_1,
    ),
    # --- Tier 2: Standard real-time streaming (<1200ms TTFT) ---
    "hin": LanguageMetadata(
        code="hin",
        bcp47="hi-IN",
        name_en="Hindi",
        name_native="हिन्दी",
        tier=LanguageTier.TIER_2,
    ),
    "por": LanguageMetadata(
        code="por",
        bcp47="pt-BR",
        name_en="Portuguese",
        name_native="Português",
        tier=LanguageTier.TIER_2,
    ),
    "ara": LanguageMetadata(
        code="ara",
        bcp47="ar-SA",
        name_en="Arabic",
        name_native="العربية",
        tier=LanguageTier.TIER_2,
    ),
    "rus": LanguageMetadata(
        code="rus",
        bcp47="ru-RU",
        name_en="Russian",
        name_native="Русский",
        tier=LanguageTier.TIER_2,
    ),
    "ita": LanguageMetadata(
        code="ita",
        bcp47="it-IT",
        name_en="Italian",
        name_native="Italiano",
        tier=LanguageTier.TIER_2,
    ),
    "kor": LanguageMetadata(
        code="kor",
        bcp47="ko-KR",
        name_en="Korean",
        name_native="한국어",
        tier=LanguageTier.TIER_2,
    ),
    "tur": LanguageMetadata(
        code="tur",
        bcp47="tr-TR",
        name_en="Turkish",
        name_native="Türkçe",
        tier=LanguageTier.TIER_2,
    ),
    "nld": LanguageMetadata(
        code="nld",
        bcp47="nl-NL",
        name_en="Dutch",
        name_native="Nederlands",
        tier=LanguageTier.TIER_2,
    ),
    "pol": LanguageMetadata(
        code="pol",
        bcp47="pl-PL",
        name_en="Polish",
        name_native="Polski",
        tier=LanguageTier.TIER_2,
    ),
    "swe": LanguageMetadata(
        code="swe",
        bcp47="sv-SE",
        name_en="Swedish",
        name_native="Svenska",
        tier=LanguageTier.TIER_2,
    ),
    "vie": LanguageMetadata(
        code="vie",
        bcp47="vi-VN",
        name_en="Vietnamese",
        name_native="Tiếng Việt",
        tier=LanguageTier.TIER_2,
    ),
    "ind": LanguageMetadata(
        code="ind",
        bcp47="id-ID",
        name_en="Indonesian",
        name_native="Bahasa Indonesia",
        tier=LanguageTier.TIER_2,
    ),
}


def normalize_code(code: str) -> str:
    """Normalizes an ISO-639-3 language string to lower-case stripped format."""
    return code.strip().lower()


def get_language(code: str) -> LanguageMetadata | None:
    """Retrieve metadata for an ISO-639-3 language code."""
    return SUPPORTED_LANGUAGES.get(normalize_code(code))


def is_supported(code: str) -> bool:
    """Check if an ISO-639-3 language code is cataloged in the platform."""
    return normalize_code(code) in SUPPORTED_LANGUAGES


def get_tier_languages(tier: LanguageTier) -> list[LanguageMetadata]:
    """Retrieve all cataloged languages belonging to a specific tier."""
    return [lang for lang in SUPPORTED_LANGUAGES.values() if lang.tier == tier]


def is_translation_supported(source: str, target: str) -> bool:
    """Determine whether direct streaming translation is supported between two languages."""
    src = get_language(source)
    tgt = get_language(target)
    if not src or not tgt:
        return False
    return src.supports_nmt and tgt.supports_nmt


def validate_language_pair(source: str, target: str) -> tuple[bool, str | None]:
    """Validates language pair for translation session setup.

    Returns:
        tuple of (is_valid, error_reason_if_any)
    """
    src_norm = normalize_code(source)
    tgt_norm = normalize_code(target)

    if src_norm == tgt_norm:
        return True, None

    src = get_language(src_norm)
    if not src:
        return False, f"Source language '{source}' is not supported."

    tgt = get_language(tgt_norm)
    if not tgt:
        return False, f"Target language '{target}' is not supported."

    if not src.supports_nmt or not tgt.supports_nmt:
        return False, f"Translation between '{src.name_en}' and '{tgt.name_en}' is unavailable."

    return True, None
