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


@app.options("/{full_path:path}", include_in_schema=False)
async def preflight_fallback(full_path: str, request: Request) -> Response:
    """Preflight OPTIONS fallback handler ensuring cross-origin requests always succeed."""
    origin = request.headers.get("origin")
    headers = {
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": request.headers.get(
            "access-control-request-headers",
            "Authorization, Content-Type, Accept, X-Requested-With, X-Tenant-Id",
        ),
        "Access-Control-Max-Age": "86400",
    }
    if origin and origin != "null":
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
    else:
        headers["Access-Control-Allow-Origin"] = "*"
    return Response(status_code=200, headers=headers)


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
