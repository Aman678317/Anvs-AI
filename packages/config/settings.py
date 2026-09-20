"""Unified Application Configuration Loader using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # System & Environment
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="multilingual-ai-meeting-platform", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # API & Gateways
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_secret_key: str = Field(
        default="dev-secret-key-change-in-production-64-bytes-min", alias="API_SECRET_KEY"
    )
    cors_origins: list[str] = Field(default=["*"], alias="CORS_ORIGINS")

    ws_host: str = Field(default="0.0.0.0", alias="WS_HOST")
    ws_port: int = Field(default=8001, alias="WS_PORT")

    # Database & Cache
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgrespassword@localhost:5432/meeting_platform",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # LiveKit WebRTC SFU
    livekit_url: str = Field(default="ws://localhost:7880", alias="LIVEKIT_URL")
    livekit_api_key: str = Field(default="devkey", alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(default="secret", alias="LIVEKIT_API_SECRET")

    # Audio Pipeline Invariants
    audio_sample_rate: int = Field(default=16000, alias="AUDIO_INCOMING_SAMPLE_RATE")
    audio_channels: int = Field(default=1, alias="AUDIO_CHANNELS")
    audio_watermark_freq_hz: int = Field(default=20000, alias="TTS_WATERMARK_FREQUENCY_HZ")

    # Authentication & Supabase (PR-05)
    supabase_url: str = Field(default="https://example.supabase.co", alias="SUPABASE_URL")
    supabase_jwt_secret: str = Field(
        default="dev-supabase-jwt-secret-key-32-chars-min-change-in-prod",
        alias="SUPABASE_JWT_SECRET",
    )
    supabase_jwt_algorithm: str = Field(default="HS256", alias="SUPABASE_JWT_ALGORITHM")
    jwt_issuer: str | None = Field(default=None, alias="JWT_ISSUER")
    jwt_audience: str | None = Field(default=None, alias="JWT_AUDIENCE")
    session_ticket_ttl_seconds: int = Field(default=300, alias="SESSION_TICKET_TTL_SECONDS")

    # Speech-to-Text STT Worker (PR-09)
    stt_engine_type: str = Field(default="mock", alias="STT_ENGINE_TYPE")
    stt_model_size: str = Field(default="base", alias="STT_MODEL_SIZE")
    stt_device: str = Field(default="cpu", alias="STT_DEVICE")
    stt_compute_type: str = Field(default="default", alias="STT_COMPUTE_TYPE")
    stt_consumer_group: str = Field(default="stt-workers-group", alias="STT_CONSUMER_GROUP")
    stt_default_language: str = Field(default="eng", alias="STT_DEFAULT_LANGUAGE")


settings = Settings()
