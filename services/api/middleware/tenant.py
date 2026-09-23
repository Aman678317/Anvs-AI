"""Tenant Context Middleware & Authentication Dependencies."""

from collections.abc import AsyncGenerator

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from packages.auth import (
    AuthenticatedUser,
    AuthenticationError,
    verify_token,
)
from packages.database.session import get_tenant_session


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Intercepts requests, extracts JWT claims, and injects tenant context into request.state."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        auth_header = request.headers.get("Authorization")
        request.state.user = None
        request.state.tenant_id = None

        # CORS preflight OPTIONS and webhook endpoints bypass user token inspection
        if request.method == "OPTIONS" or request.url.path.endswith("/webhook"):
            return await call_next(request)

        if auth_header:
            parts = auth_header.strip().split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                try:
                    user: AuthenticatedUser = verify_token(token)
                    request.state.user = user
                    request.state.tenant_id = user.tenant_id
                except AuthenticationError as e:
                    # If an explicit Bearer token is provided and invalid/expired,
                    # reject immediately with 401
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": str(e)},
                        headers={"WWW-Authenticate": "Bearer"},
                    )

        response = await call_next(request)
        return response


def get_current_user(request: Request) -> AuthenticatedUser:
    """FastAPI dependency to retrieve the verified user from request state."""
    user = getattr(request.state, "user", None)
    if not user or not isinstance(user, AuthenticatedUser):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_tenant_id(request: Request) -> str:
    """FastAPI dependency to retrieve the validated tenant ID from request state."""
    user = get_current_user(request)
    return user.tenant_id


async def get_authenticated_tenant_session(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an AsyncSession configured with PostgreSQL RLS for the authenticated tenant."""
    tenant_id = get_current_tenant_id(request)
    async with get_tenant_session(tenant_id) as session:
        yield session
