"""Unified Application Configuration Loader using Pydantic Settings."""

from typing import List
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
    api_secret_key: str = Field(default="dev-secret-key-change-in-production-64-bytes-min", alias="API_SECRET_KEY")
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")

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


settings = Settings()
