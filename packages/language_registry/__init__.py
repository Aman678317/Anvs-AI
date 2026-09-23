"""Language Registry Python Package."""

from .languages import (
    SUPPORTED_LANGUAGES,
    LanguageMetadata,
    LanguageTier,
    get_language,
    get_optimal_nmt_model,
    get_tier_languages,
    is_indic_language,
    is_supported,
    is_translation_supported,
    normalize_code,
    validate_language_pair,
)

__all__ = [
    "SUPPORTED_LANGUAGES",
    "LanguageMetadata",
    "LanguageTier",
    "get_language",
    "get_optimal_nmt_model",
    "get_tier_languages",
    "is_indic_language",
    "is_supported",
    "is_translation_supported",
    "normalize_code",
    "validate_language_pair",
]
