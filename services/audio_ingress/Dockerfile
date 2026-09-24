# syntax=docker/dockerfile:1.4
# ==============================================================================
# Production Dockerfile: Audio Ingress Daemon (P0 Runtime Wiring)
# LiveKit RTC watcher bot that subscribes to human participant audio tracks,
# enforces the Human Source Gate (Invariant #1), and streams segmented PCM
# into the Redis "audio" event stream for the STT fleet.
# ==============================================================================

# Stage 1: Build & Dependency Resolution
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install . livekit-rtc>=0.7.0

# Stage 2: Final Runtime Minimal Container
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:/install/lib/python3.11/site-packages" \
    APP_ENV="production" \
    MEETING_ID="default_meeting"

# libgomp / libc needed by native livekit-rtc bindings; curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -d /app appuser

COPY --from=builder /install /install
COPY packages /app/packages
COPY services /app/services
COPY pyproject.toml /app/pyproject.toml

RUN chown -R appuser:appgroup /app

USER 10001:10001

CMD ["python", "-m", "services.audio_ingress.main"]
