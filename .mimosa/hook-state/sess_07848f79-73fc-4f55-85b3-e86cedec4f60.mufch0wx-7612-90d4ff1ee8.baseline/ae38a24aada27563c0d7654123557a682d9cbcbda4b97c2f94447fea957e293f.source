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
    is_indic: bool = False
    nmt_model: str = "facebook/nllb-200-distilled-600M"
    licensing: str = "MIT"


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
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
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
    # --- Indic Languages (DEC-01: ai4bharat/indictrans2-1B) ---
    "mar": LanguageMetadata(
        code="mar",
        bcp47="mr-IN",
        name_en="Marathi",
        name_native="मराठी",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
    "ben": LanguageMetadata(
        code="ben",
        bcp47="bn-IN",
        name_en="Bengali",
        name_native="বাংলা",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
    "tam": LanguageMetadata(
        code="tam",
        bcp47="ta-IN",
        name_en="Tamil",
        name_native="தமிழ்",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
    "tel": LanguageMetadata(
        code="tel",
        bcp47="te-IN",
        name_en="Telugu",
        name_native="తెలుగు",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
    "guj": LanguageMetadata(
        code="guj",
        bcp47="gu-IN",
        name_en="Gujarati",
        name_native="ગુજરાતી",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
    "kan": LanguageMetadata(
        code="kan",
        bcp47="kn-IN",
        name_en="Kannada",
        name_native="ಕನ್ನಡ",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
    "mal": LanguageMetadata(
        code="mal",
        bcp47="ml-IN",
        name_en="Malayalam",
        name_native="മലയാളം",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
    "pan": LanguageMetadata(
        code="pan",
        bcp47="pa-IN",
        name_en="Punjabi",
        name_native="ਪੰਜਾਬੀ",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
    "urd": LanguageMetadata(
        code="urd",
        bcp47="ur-IN",
        name_en="Urdu",
        name_native="اردو",
        tier=LanguageTier.TIER_2,
        is_indic=True,
        nmt_model="ai4bharat/indictrans2-1B",
        licensing="CC-BY-NC-4.0",
    ),
}

ISO_639_1_TO_639_3: dict[str, str] = {
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
    "bn": "ben",
    "ta": "tam",
    "te": "tel",
    "mr": "mar",
    "id": "ind",
    "gu": "guj",
    "kn": "kan",
    "ml": "mal",
    "pa": "pan",
    "ur": "urd",
}


def normalize_code(code: str) -> str:
    """Normalizes an ISO-639-1 or ISO-639-3 language string to lower-case ISO-639-3 format."""
    cleaned = code.strip().lower()
    # Strip BCP-47 regional suffix if present (e.g. en-US -> en)
    primary = cleaned.split("-")[0] if "-" in cleaned else cleaned
    return ISO_639_1_TO_639_3.get(primary, cleaned)


def get_language(code: str) -> LanguageMetadata | None:
    """Retrieve metadata for an ISO-639-3 language code (or alias)."""
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


def is_indic_language(code: str) -> bool:
    """Checks whether the specified language belongs to the Indic language family."""
    lang = get_language(code)
    return lang.is_indic if lang else False


def get_optimal_nmt_model(source: str, target: str) -> str:
    """Implements DEC-01: Routes Indic language pairs to IndicTrans2 and others to NLLB-200.

    - Indic pairs (e.g. eng->hin, hin->mar, mar->eng) route to 'ai4bharat/indictrans2-1B'.
    - Global pairs (e.g. eng->spa, fra->deu, zho->jpn) route to 'facebook/nllb-200-distilled-600M'.
    """
    if is_indic_language(source) or is_indic_language(target):
        return "ai4bharat/indictrans2-1B"
    return "facebook/nllb-200-distilled-600M"
