# syntax=docker/dockerfile:1.4
# ==============================================================================
# Compose Smoke Test Harness (P0 Runtime Wiring CI Gate)
# Feeds synthetic human speech through AudioIngressService against the real
# redis container and fails non-zero unless the source-segment ("audio")
# stream depth for the meeting becomes > 0 — proving PCM actually reaches
# Redis end-to-end. Also asserts Invariant #3 loop rejection by feeding
# watermarked (synthetic TTS) audio back through ingress.
# ==============================================================================

FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV="development"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir . numpy redis

COPY packages /app/packages
COPY services /app/services
COPY infrastructure/docker/smoke/run_smoke.py /app/run_smoke.py

CMD ["python", "/app/run_smoke.py"]
