"""Phase 3 — TDD: the POST /requests/{id}/call endpoint and its double-call guard."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_file}")
    with TestClient(app) as test_client:
        yield test_client


def _create_request(client):
    resp = client.post(
        "/requests",
        json={
            "isp_phone": "18005551234",
            "account_number": "1234567890",
            "pin": "4321",
            "business_name": "Vivant Corp",
            "business_address": "2727 Lyndon, 75234",
        },
    )
    return resp.json()["id"]


def test_call_starts_and_sets_status_calling(client):
    req_id = _create_request(client)

    resp = client.post(f"/requests/{req_id}/call")
    assert resp.status_code == 201
    body = resp.json()
    assert body["request_id"] == req_id
    assert body["provider_call_id"].startswith("stub-call-")
    assert body["status"] == "queued"

    # The request itself should now read as "calling".
    one = client.get(f"/requests/{req_id}")
    assert one.json()["status"] == "calling"


def test_second_call_is_blocked_while_first_is_active(client):
    req_id = _create_request(client)
    first = client.post(f"/requests/{req_id}/call")
    assert first.status_code == 201

    second = client.post(f"/requests/{req_id}/call")
    assert second.status_code == 409  # blocked — already in progress


def test_call_on_missing_request_returns_404(client):
    resp = client.post("/requests/999/call")
    assert resp.status_code == 404
