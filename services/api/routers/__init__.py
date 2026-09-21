"""Control Plane API Routers Package."""

from .admin import get_admin_user
from .admin import router as admin_router
from .auth import router as auth_router
from .rooms import router as rooms_router

__all__ = ["admin_router", "auth_router", "get_admin_user", "rooms_router"]
