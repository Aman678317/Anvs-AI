"""FastAPI Control Plane Entrypoint (Services / API)."""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from packages.config import settings
from packages.observability import generate_metrics_response
from services.api.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TenantContextMiddleware,
)
from services.api.routers import (
    admin_router,
    auth_router,
    health_router,
    rooms_router,
)

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

# Middleware stack (LIFO execution order - CORSMiddleware is outermost)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=(
        r"^https?://.*$"
        if (settings.app_env != "production" or settings.debug)
        else r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(admin_router)


ALLOWED_ORIGINS: set[str] = set(settings.cors_origins) | {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}


@app.options("/{path:path}", include_in_schema=False)
async def preflight_handler(request: Request) -> Response:
    """Preflight OPTIONS fallback handler ensuring cross-origin requests always succeed."""
    origin = request.headers.get("origin")

    headers = {
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": request.headers.get(
            "access-control-request-headers",
            "Content-Type, Authorization, X-Requested-With, X-Tenant-Id",
        ),
        "Access-Control-Max-Age": "86400",
    }

    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"

    return Response(status_code=204, headers=headers)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.api.main:app", host="0.0.0.0", port=8000, reload=True)
