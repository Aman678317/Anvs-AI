"""Language Registry and Tier Classification based on Documents 10, 12, 13, 14."""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel


class LanguageTier(str, Enum):
    TIER_1 = "TIER_1"  # Ultra-low-latency real-time streaming (<500ms TTFT)
    TIER_2 = "TIER_2"  # Standard real-time streaming (<1200ms TTFT)
    TIER_3 = "TIER_3"  # High-latency / batch translation only


class LanguageMetadata(BaseModel):
    code: str              # ISO-639-3 (e.g. 'eng', 'spa', 'hin')
    bcp47: str             # BCP-47 tag (e.g. 'en-US', 'es-ES', 'hi-IN')
    name_en: str           # English Name
    name_native: str       # Native Name
    tier: LanguageTier
    supports_stt: bool = True
    supports_nmt: bool = True
    supports_tts: bool = True


SUPPORTED_LANGUAGES: Dict[str, LanguageMetadata] = {
    "eng": LanguageMetadata(code="eng", bcp47="en-US", name_en="English", name_native="English", tier=LanguageTier.TIER_1),
    "spa": LanguageMetadata(code="spa", bcp47="es-ES", name_en="Spanish", name_native="Español", tier=LanguageTier.TIER_1),
    "fra": LanguageMetadata(code="fra", bcp47="fr-FR", name_en="French", name_native="Français", tier=LanguageTier.TIER_1),
    "deu": LanguageMetadata(code="deu", bcp47="de-DE", name_en="German", name_native="Deutsch", tier=LanguageTier.TIER_1),
    "zho": LanguageMetadata(code="zho", bcp47="zh-CN", name_en="Mandarin Chinese", name_native="中文", tier=LanguageTier.TIER_1),
    "jpn": LanguageMetadata(code="jpn", bcp47="ja-JP", name_en="Japanese", name_native="日本語", tier=LanguageTier.TIER_1),
    "hin": LanguageMetadata(code="hin", bcp47="hi-IN", name_en="Hindi", name_native="हिन्दी", tier=LanguageTier.TIER_2),
    "por": LanguageMetadata(code="por", bcp47="pt-BR", name_en="Portuguese", name_native="Português", tier=LanguageTier.TIER_2),
    "ara": LanguageMetadata(code="ara", bcp47="ar-SA", name_en="Arabic", name_native="العربية", tier=LanguageTier.TIER_2),
    "rus": LanguageMetadata(code="rus", bcp47="ru-RU", name_en="Russian", name_native="Русский", tier=LanguageTier.TIER_2),
    "ita": LanguageMetadata(code="ita", bcp47="it-IT", name_en="Italian", name_native="Italiano", tier=LanguageTier.TIER_2),
    "kor": LanguageMetadata(code="kor", bcp47="ko-KR", name_en="Korean", name_native="한국어", tier=LanguageTier.TIER_2),
}


def get_language(code: str) -> Optional[LanguageMetadata]:
    """Retrieve metadata for an ISO-639-3 language code."""
    return SUPPORTED_LANGUAGES.get(code.lower())


def is_supported(code: str) -> bool:
    """Check if an ISO-639-3 language code is supported."""
    return code.lower() in SUPPORTED_LANGUAGES
