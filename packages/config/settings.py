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

    # Neural Machine Translation NMT Worker (PR-10)
    nmt_engine_type: str = Field(default="mock", alias="NMT_ENGINE_TYPE")
    nmt_model_name: str = Field(default="facebook/nllb-200-distilled-600M", alias="NMT_MODEL_NAME")
    nmt_device: str = Field(default="cpu", alias="NMT_DEVICE")
    nmt_consumer_group: str = Field(default="nmt-workers-group", alias="NMT_CONSUMER_GROUP")
    nmt_context_window_size: int = Field(default=2, alias="NMT_CONTEXT_WINDOW_SIZE")
    nmt_default_target_languages: list[str] = Field(
        default=["spa", "fra", "deu", "zho", "jpn"], alias="NMT_DEFAULT_TARGET_LANGUAGES"
    )

    # Text-to-Speech TTS Worker (PR-11)
    tts_engine_type: str = Field(default="mock", alias="TTS_ENGINE_TYPE")
    tts_model_name: str = Field(default="coqui/XTTS-v2", alias="TTS_MODEL_NAME")
    tts_device: str = Field(default="cpu", alias="TTS_DEVICE")
    tts_consumer_group: str = Field(default="tts-workers-group", alias="TTS_CONSUMER_GROUP")
    tts_sample_rate: int = Field(default=48000, alias="TTS_SAMPLE_RATE")
    tts_watermark_enabled: bool = Field(default=True, alias="TTS_WATERMARK_ENABLED")
    tts_watermark_freq_hz: float = Field(default=20000.0, alias="TTS_WATERMARK_FREQ_HZ")
    tts_default_voice_id: str = Field(default="default_neutral", alias="TTS_DEFAULT_VOICE_ID")

    # Speaker Diarization Worker (PR-12)
    speaker_engine_type: str = Field(default="mock", alias="SPEAKER_ENGINE_TYPE")
    speaker_model_name: str = Field(
        default="pyannote/speaker-diarization-3.1",
        alias="SPEAKER_MODEL_NAME",
    )
    speaker_device: str = Field(default="cpu", alias="SPEAKER_DEVICE")
    speaker_consumer_group: str = Field(
        default="speaker-workers-group",
        alias="SPEAKER_CONSUMER_GROUP",
    )
    speaker_embedding_dim: int = Field(default=512, alias="SPEAKER_EMBEDDING_DIM")
    speaker_similarity_threshold: float = Field(
        default=0.75,
        alias="SPEAKER_SIMILARITY_THRESHOLD",
    )

    # Meeting Assistant Worker (PR-13)
    assistant_engine_type: str = Field(default="mock", alias="ASSISTANT_ENGINE_TYPE")
    assistant_model_name: str = Field(default="gpt-4o-mini", alias="ASSISTANT_MODEL_NAME")
    assistant_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="ASSISTANT_EMBEDDING_MODEL",
    )
    assistant_embedding_dim: int = Field(default=1536, alias="ASSISTANT_EMBEDDING_DIM")
    assistant_consumer_group: str = Field(
        default="assistant-workers-group",
        alias="ASSISTANT_CONSUMER_GROUP",
    )
    assistant_top_k: int = Field(default=5, alias="ASSISTANT_TOP_K")
    assistant_similarity_threshold: float = Field(
        default=0.60,
        alias="ASSISTANT_SIMILARITY_THRESHOLD",
    )

    # Pipeline Orchestrator & Backpressure (PR-16)
    orchestrator_queue_high_threshold: int = Field(
        default=50,
        alias="ORCHESTRATOR_QUEUE_HIGH_THRESHOLD",
    )
    orchestrator_queue_critical_threshold: int = Field(
        default=100,
        alias="ORCHESTRATOR_QUEUE_CRITICAL_THRESHOLD",
    )
    orchestrator_worker_timeout_sec: float = Field(
        default=3.0,
        alias="ORCHESTRATOR_WORKER_TIMEOUT_SEC",
    )
    orchestrator_dlq_max_retries: int = Field(
        default=3,
        alias="ORCHESTRATOR_DLQ_MAX_RETRIES",
    )
    orchestrator_cooldown_period_sec: float = Field(
        default=10.0,
        alias="ORCHESTRATOR_COOLDOWN_PERIOD_SEC",
    )
    orchestrator_stream_maxlen: int = Field(
        default=10000,
        alias="ORCHESTRATOR_STREAM_MAXLEN",
    )

    # Security Hardening & Cryptography (PR-18)
    security_master_encryption_key: str = Field(
        default="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        alias="SECURITY_MASTER_ENCRYPTION_KEY",
    )
    security_rate_limit_per_minute: int = Field(
        default=120,
        alias="SECURITY_RATE_LIMIT_PER_MINUTE",
    )
    security_rate_limit_burst: int = Field(
        default=30,
        alias="SECURITY_RATE_LIMIT_BURST",
    )
    security_rate_limit_enabled: bool = Field(
        default=True,
        alias="SECURITY_RATE_LIMIT_ENABLED",
    )


settings = Settings()
