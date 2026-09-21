# syntax=docker/dockerfile:1.4
# ==============================================================================
# Production Dockerfile: Realtime WebSocket Gateway (PR-20)
# High-throughput asynchronous WebSocket routing container
# ==============================================================================

# Stage 1: Build & Dependencies
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
    pip install --prefix=/install .

# Stage 2: Minimal Runtime
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:/install/lib/python3.11/site-packages" \
    APP_ENV="production" \
    GATEWAY_PORT=8001

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -d /app appuser

COPY --from=builder /install /install
COPY packages /app/packages
COPY services/realtime_gateway /app/services/realtime_gateway
COPY pyproject.toml /app/pyproject.toml

RUN chown -R appuser:appgroup /app

USER 10001:10001

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/healthz || exit 1

CMD ["python", "-m", "uvicorn", "services.realtime_gateway.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2", "--ws", "websockets"]
