"""Unit tests for TenantContextMiddleware and Auth FastAPI Dependencies."""

import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from packages.auth import AuthenticatedUser, create_access_token
from packages.contracts import ParticipantRole
from services.api.middleware.tenant import (
    TenantContextMiddleware,
    get_current_tenant_id,
    get_current_user,
)


@pytest.fixture
def app_with_middleware() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(TenantContextMiddleware)

    @test_app.get("/public")
    async def public_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/protected")
    async def protected_endpoint(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict[str, str]:
        return {
            "user_id": current_user.user_id,
            "tenant_id": current_user.tenant_id,
            "role": current_user.role.value,
        }

    @test_app.get("/tenant")
    async def tenant_only_endpoint(
        tenant_id: str = Depends(get_current_tenant_id),
    ) -> dict[str, str]:
        return {"tenant_id": tenant_id}

    return test_app


@pytest.fixture
def client(app_with_middleware: FastAPI) -> TestClient:
    return TestClient(app_with_middleware)


@pytest.fixture
def sample_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="operator@telecom.org",
        role=ParticipantRole.CO_HOST,
        display_name="Network Operator",
    )


@pytest.mark.unit
def test_public_endpoint_unauthenticated(client: TestClient) -> None:
    response = client.get("/public")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_protected_endpoint_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/protected")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


@pytest.mark.unit
def test_protected_endpoint_with_invalid_token_returns_401(client: TestClient) -> None:
    headers = {"Authorization": "Bearer invalid.token.value"}
    response = client.get("/protected", headers=headers)
    assert response.status_code == 401
    assert "Invalid access token" in response.json()["detail"]


@pytest.mark.unit
def test_protected_endpoint_with_valid_token(
    client: TestClient, sample_user: AuthenticatedUser
) -> None:
    token = create_access_token(sample_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/protected", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == sample_user.user_id
    assert data["tenant_id"] == sample_user.tenant_id
    assert data["role"] == "CO_HOST"


@pytest.mark.unit
def test_tenant_id_dependency_extraction(
    client: TestClient, sample_user: AuthenticatedUser
) -> None:
    token = create_access_token(sample_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/tenant", headers=headers)
    assert response.status_code == 200
    assert response.json()["tenant_id"] == sample_user.tenant_id
