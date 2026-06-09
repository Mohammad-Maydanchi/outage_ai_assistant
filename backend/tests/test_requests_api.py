"""Phase 1 — TDD: the /requests web endpoints (create, list, get) work and
mask secrets in their responses. Runs against a fresh temporary database.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_file}")
    with TestClient(app) as test_client:  # 'with' runs startup → creates the table
        yield test_client


def _payload(name="Vivant Corp"):
    return {
        "isp_phone": "18005551234",
        "account_number": "1234567890",
        "pin": "4321",
        "business_name": name,
        "business_address": "2727 Lyndon, 75234",
    }


def test_create_returns_masked_secrets(client):
    resp = client.post("/requests", json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] >= 1
    assert body["status"] == "new"
    assert body["account_number"] == "••••7890"  # masked
    assert body["pin"] == "••••"  # fully hidden
    assert body["business_name"] == "Vivant Corp"


def test_create_missing_required_field_is_rejected(client):
    bad = _payload()
    del bad["account_number"]
    resp = client.post("/requests", json=bad)
    assert resp.status_code == 422  # validation error


def test_list_and_get_one(client):
    client.post("/requests", json=_payload("First"))
    second = client.post("/requests", json=_payload("Second"))
    second_id = second.json()["id"]

    listed = client.get("/requests")
    assert listed.status_code == 200
    assert len(listed.json()) == 2
    assert listed.json()[0]["business_name"] == "Second"  # newest first

    one = client.get(f"/requests/{second_id}")
    assert one.status_code == 200
    assert one.json()["business_name"] == "Second"
    assert one.json()["account_number"] == "••••7890"  # still masked


def test_get_missing_returns_404(client):
    resp = client.get("/requests/999")
    assert resp.status_code == 404
