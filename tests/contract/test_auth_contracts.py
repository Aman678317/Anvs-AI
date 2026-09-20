"""Contract tests for Authentication API endpoints and PR-02 Domain Contracts."""

import uuid

import pytest
from fastapi.testclient import TestClient

from packages.contracts import AuthTokenRequest, AuthTokenResponse, ParticipantRole
from services.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.contract
def test_issue_token_contract_roundtrip(client: TestClient) -> None:
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    email = "lead.engineer@enterprise.io"

    request_contract = AuthTokenRequest(
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
        role=ParticipantRole.HOST,
    )

    response = client.post("/api/v1/auth/token", json=request_contract.model_dump())
    assert response.status_code == 200

    response_data = response.json()
    response_contract = AuthTokenResponse(**response_data)

    assert response_contract.user_id == user_id
    assert response_contract.tenant_id == tenant_id
    assert response_contract.token_type == "Bearer"
    assert response_contract.expires_in_sec == 3600
    assert len(response_contract.access_token) > 20


@pytest.mark.contract
def test_authenticated_me_and_ticket_flow(client: TestClient) -> None:
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    email = "researcher@lab.org"

    token_req = AuthTokenRequest(
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
        role=ParticipantRole.PARTICIPANT,
    )
    token_resp = client.post("/api/v1/auth/token", json=token_req.model_dump())
    assert token_resp.status_code == 200
    access_token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Verify GET /api/v1/auth/me
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user_id"] == user_id
    assert me_data["tenant_id"] == tenant_id
    assert me_data["email"] == email
    assert me_data["role"] == "PARTICIPANT"

    # 2. Verify POST /api/v1/auth/ticket
    meeting_id = str(uuid.uuid4())
    ticket_resp = client.post(
        "/api/v1/auth/ticket",
        headers=headers,
        json={"meeting_id": meeting_id, "ttl_seconds": 180},
    )
    assert ticket_resp.status_code == 200
    ticket_data = ticket_resp.json()
    assert ticket_data["meeting_id"] == meeting_id
    assert ticket_data["user_id"] == user_id
    assert ticket_data["tenant_id"] == tenant_id
    assert ticket_data["expires_in_sec"] == 180
    assert "ticket" in ticket_data
