"""Unit tests for the Multi-Tier Language Registry and Pair Validation."""

import pytest

from packages.language_registry import (
    LanguageTier,
    get_language,
    get_tier_languages,
    is_supported,
    is_translation_supported,
    normalize_code,
    validate_language_pair,
)


@pytest.mark.unit
def test_normalize_code() -> None:
    assert normalize_code(" ENG ") == "eng"
    assert normalize_code("Spa") == "spa"
    assert normalize_code("hin") == "hin"


@pytest.mark.unit
def test_tier_one_languages_catalog() -> None:
    tier_1 = get_tier_languages(LanguageTier.TIER_1)
    tier_1_codes = {lang.code for lang in tier_1}
    # Per Document 10: eng, spa, fra, deu, zho, jpn are Tier 1 streaming
    expected_tier_1 = {"eng", "spa", "fra", "deu", "zho", "jpn"}
    assert expected_tier_1.issubset(tier_1_codes)

    for lang in tier_1:
        assert lang.supports_stt is True
        assert lang.supports_nmt is True
        assert lang.supports_tts is True
        assert lang.supports_voice_clone is True


@pytest.mark.unit
def test_tier_two_languages_catalog() -> None:
    tier_2 = get_tier_languages(LanguageTier.TIER_2)
    tier_2_codes = {lang.code for lang in tier_2}
    expected_tier_2 = {"hin", "por", "ara", "rus", "ita", "kor", "tur", "nld"}
    assert expected_tier_2.issubset(tier_2_codes)


@pytest.mark.unit
def test_get_language_metadata() -> None:
    hin = get_language("hin")
    assert hin is not None
    assert hin.bcp47 == "hi-IN"
    assert hin.name_en == "Hindi"
    assert hin.name_native == "हिन्दी"
    assert hin.tier == LanguageTier.TIER_2

    zho = get_language("zho")
    assert zho is not None
    assert zho.bcp47 == "zh-CN"
    assert zho.name_en == "Mandarin Chinese"


@pytest.mark.unit
def test_unsupported_language_behavior() -> None:
    assert not is_supported("xyz")
    assert get_language("xyz") is None
    assert not is_translation_supported("eng", "xyz")


@pytest.mark.unit
def test_validate_language_pair() -> None:
    # Identical language pair is always valid (pass-through)
    is_valid, err = validate_language_pair("eng", "eng")
    assert is_valid is True
    assert err is None

    # Valid bidirectional streaming pair
    is_valid, err = validate_language_pair("eng", "spa")
    assert is_valid is True
    assert err is None

    # Unsupported source
    is_valid, err = validate_language_pair("foo", "eng")
    assert is_valid is False
    assert "Source language 'foo' is not supported" in str(err)

    # Unsupported target
    is_valid, err = validate_language_pair("eng", "bar")
    assert is_valid is False
    assert "Target language 'bar' is not supported" in str(err)
