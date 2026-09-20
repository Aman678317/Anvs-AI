"""Authentication and Authorization package (Supabase JWT & RBAC)."""

from typing import Optional
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    roles: list[str] = []


__all__ = ["AuthenticatedUser"]
