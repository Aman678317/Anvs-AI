"""Unit tests for Unified Configuration and Production Fail-Fast Invariants (PR-01 & DEC-06)."""

import pytest
from pydantic import ValidationError

from packages.config.settings import Settings


@pytest.mark.unit
def test_development_settings_defaults() -> None:
    """Verifies that development environment boots cleanly with default mock engines."""
    cfg = Settings(
        APP_ENV="development",
        STT_ENGINE_TYPE="mock",
        NMT_ENGINE_TYPE="mock",
        TTS_ENGINE_TYPE="mock",
        SPEAKER_ENGINE_TYPE="mock",
        ASSISTANT_ENGINE_TYPE="mock",
    )
    assert cfg.app_env == "development"
    assert cfg.stt_engine_type == "mock"
    assert cfg.audio_watermark_freq_hz == 20000


@pytest.mark.unit
def test_production_settings_fails_with_mock_engines() -> None:
    """Verifies that production environment fails fast if mock engines are configured (DEC-06)."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            API_SECRET_KEY="a" * 64,
            SUPABASE_JWT_SECRET="b" * 32,
            STT_ENGINE_TYPE="mock",
        )
    err_str = str(exc_info.value)
    assert (
        "Production environment (APP_ENV=production) cannot boot with mock engine defaults"
        in err_str
    )
    assert "STT_ENGINE_TYPE" in err_str


@pytest.mark.unit
def test_production_settings_fails_with_dev_secrets() -> None:
    """Verifies that production environment fails fast if default dev secrets are left unchanged."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            STT_ENGINE_TYPE="whisper",
            NMT_ENGINE_TYPE="nllb",
            TTS_ENGINE_TYPE="piper",
            SPEAKER_ENGINE_TYPE="pyannote",
            ASSISTANT_ENGINE_TYPE="openai",
            # API_SECRET_KEY left as default containing 'dev-secret-key'
        )
    err_str = str(exc_info.value)
    assert "Production environment cannot use default API_SECRET_KEY" in err_str


@pytest.mark.unit
def test_production_settings_success() -> None:
    """Verifies that production environment boots cleanly when real engines and secure secrets are configured."""
    cfg = Settings(
        APP_ENV="production",
        API_SECRET_KEY="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        SUPABASE_JWT_SECRET="production-secure-jwt-secret-key-32-chars",
        STT_ENGINE_TYPE="whisper",
        NMT_ENGINE_TYPE="nllb",
        TTS_ENGINE_TYPE="piper",
        SPEAKER_ENGINE_TYPE="pyannote",
        ASSISTANT_ENGINE_TYPE="openai",
    )
    assert cfg.app_env == "production"
    assert cfg.stt_engine_type == "whisper"
    assert cfg.tts_engine_type == "piper"


@pytest.mark.unit
def test_nvidia_settings_configuration() -> None:
    """Verifies that NVIDIA NIM configuration parameters are properly parsed."""
    cfg = Settings(
        APP_ENV="development",
        NVIDIA_API_KEY="nvapi-test-key-12345",
        NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1",
        ASSISTANT_ENGINE_TYPE="nvidia",
        ASSISTANT_MODEL_NAME="meta/llama-3.1-8b-instruct",
    )
    assert cfg.nvidia_api_key == "nvapi-test-key-12345"
    assert cfg.nvidia_base_url == "https://integrate.api.nvidia.com/v1"
    assert cfg.assistant_engine_type == "nvidia"
    assert cfg.assistant_model_name == "meta/llama-3.1-8b-instruct"


@pytest.mark.unit
def test_database_url_normalization() -> None:
    """Verifies that postgresql:// URLs are automatically normalized to postgresql+asyncpg://."""
    cfg = Settings(
        APP_ENV="development",
        DATABASE_URL="postgresql://user:pass@localhost:5432/test_db",
        DIRECT_URL="postgresql://user:pass@localhost:5432/direct_db",
    )
    assert cfg.database_url.startswith("postgresql+asyncpg://")
    assert cfg.direct_url.startswith("postgresql+asyncpg://")
