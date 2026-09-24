"""Unit tests for the Language Registry and Tier classifications."""

import pytest

from packages.language_registry import (
    LanguageTier,
    get_language,
    is_supported,
)


@pytest.mark.unit
def test_language_tier_one_lookup() -> None:
    lang = get_language("eng")
    assert lang is not None
    assert lang.code == "eng"
    assert lang.tier == LanguageTier.TIER_1
    assert lang.name_en == "English"
    assert is_supported("eng")


@pytest.mark.unit
def test_language_tier_two_lookup() -> None:
    lang = get_language("hin")
    assert lang is not None
    assert lang.code == "hin"
    assert lang.tier == LanguageTier.TIER_2
    assert lang.name_native == "हिन्दी"
    assert is_supported("hin")


@pytest.mark.unit
def test_unsupported_language() -> None:
    assert not is_supported("xyz")
    assert get_language("xyz") is None


@pytest.mark.unit
def test_supported_languages_catalog() -> None:
    from packages.language_registry import SUPPORTED_LANGUAGES

    assert len(SUPPORTED_LANGUAGES) > 0
    assert "eng" in SUPPORTED_LANGUAGES
    assert "spa" in SUPPORTED_LANGUAGES
