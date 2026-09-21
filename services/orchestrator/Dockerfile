# syntax=docker/dockerfile:1.4
# ==============================================================================
# Production Dockerfile: Pipeline Orchestrator & DLQ Manager (PR-20)
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install .

FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:/install/lib/python3.11/site-packages" \
    APP_ENV="production"

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -d /app appuser

COPY --from=builder /install /install
COPY packages /app/packages
COPY services/orchestrator /app/services/orchestrator
COPY pyproject.toml /app/pyproject.toml

RUN chown -R appuser:appgroup /app

USER 10001:10001

CMD ["python", "-m", "services.orchestrator.main"]
