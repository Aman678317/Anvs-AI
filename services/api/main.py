"""FastAPI Control Plane Entrypoint (Services / API)."""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from packages.config import settings
from packages.observability import generate_metrics_response
from services.api.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TenantContextMiddleware,
)
from services.api.routers import admin_router, auth_router, rooms_router

app = FastAPI(
    title="Multilingual AI Meeting Platform - Control Plane API",
    description=(
        "REST API for authentication, meeting lifecycle, "
        "participant coordination, and room state."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware stack (LIFO execution order)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(admin_router)


@app.get("/healthz", tags=["System"])
async def health_check() -> dict:
    """Health check endpoint for container probes and uptime monitors."""
    return {
        "status": "healthy",
        "service": "api-control-plane",
        "version": "1.0.0",
        "environment": settings.app_env,
    }


@app.get("/metrics", tags=["System"])
async def get_prometheus_metrics() -> Response:
    """Prometheus exposition metrics endpoint."""
    content, media_type = generate_metrics_response()
    return Response(content=content, media_type=media_type)


@app.get("/", tags=["System"])
async def root() -> dict:
    return {
        "platform": "Multilingual AI Meeting Platform",
        "status": "online",
        "docs": "/docs",
    }
