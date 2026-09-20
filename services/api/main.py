"""FastAPI Control Plane Entrypoint (Services / API)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.config import settings

app = FastAPI(
    title="Multilingual AI Meeting Platform - Control Plane API",
    description="REST API for authentication, meeting lifecycle, participant coordination, and room state.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["System"])
async def health_check() -> dict:
    """Health check endpoint for container probes and uptime monitors."""
    return {
        "status": "healthy",
        "service": "api-control-plane",
        "version": "1.0.0",
        "environment": settings.app_env,
    }


@app.get("/", tags=["System"])
async def root() -> dict:
    return {
        "platform": "Multilingual AI Meeting Platform",
        "status": "online",
        "docs": "/docs",
    }
