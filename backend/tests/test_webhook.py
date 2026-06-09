"""Phase 4 — TDD: the Vapi webhook (signature, logging, dedupe, out-of-order)."""

import json

import pytest
from fastapi.testclient import TestClient

from app import repository
from app.config import settings
from app.main import app
from app.models import OutageRequestCreate
from app.security import compute_signature

SECRET = "testsecret"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_file}")
    monkeypatch.setattr(settings, "vapi_webhook_secret", SECRET)
    with TestClient(app) as test_client:
        req = repository.create_request(
            OutageRequestCreate(
                isp_phone="18005551234",
                account_number="1234567890",
                pin="4321",
                business_name="Vivant Corp",
                business_address="2727 Lyndon, 75234",
            )
        )
        repository.create_call(req.id, "vapi-1", "queued")
        yield test_client


def _post(client, body, sign=True):
    raw = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if sign:
        headers["x-vapi-signature"] = compute_signature(SECRET, raw)
    return client.post("/webhooks/vapi", content=raw, headers=headers)


def test_unsigned_request_is_rejected(client):
    resp = _post(client, {"call_id": "vapi-1", "status": "ringing", "event_id": "e1"}, sign=False)
    assert resp.status_code == 401


def test_valid_event_logs_and_advances_status(client):
    resp = _post(client, {"call_id": "vapi-1", "status": "ringing", "event_id": "e1"})
    assert resp.status_code == 200
    assert resp.json()["new"] is True
    assert repository.get_call_by_provider_id("vapi-1").status == "ringing"


def test_duplicate_event_is_deduped(client):
    body = {"call_id": "vapi-1", "status": "ringing", "event_id": "e1"}
    assert _post(client, body).json()["new"] is True
    assert _post(client, body).json()["new"] is False  # same event id → ignored


def test_out_of_order_update_does_not_rewind(client):
    _post(client, {"call_id": "vapi-1", "status": "ended", "event_id": "e-end"})
    _post(client, {"call_id": "vapi-1", "status": "ringing", "event_id": "e-ring"})
    # The late "ringing" must not undo "ended".
    assert repository.get_call_by_provider_id("vapi-1").status == "ended"


def test_unknown_call_is_ignored_with_200(client):
    resp = _post(client, {"call_id": "does-not-exist", "status": "ringing", "event_id": "e1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
