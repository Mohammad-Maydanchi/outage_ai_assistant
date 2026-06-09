"""Phase 5 — TDD: the POST /requests/{id}/report endpoint.

Uses the fake extractor (no live Claude call) so the test is free and stable.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.extraction import ReportData, StubExtractor, get_extractor
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_file}")
    canned = ReportData(
        outcome="no_rep_reached",
        responder="bot",
        spoke_with="automated message",
        summary="No human reached; callback offered in 4-6 minutes.",
    )
    app.dependency_overrides[get_extractor] = lambda: StubExtractor(canned)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _new_request(client):
    return client.post(
        "/requests",
        json={
            "isp_phone": "18005551234",
            "account_number": "1234567890",
            "pin": "4321",
            "business_name": "Vivant Corp",
            "business_address": "2727 Lyndon, 75234",
        },
    ).json()["id"]


def test_generate_report_marks_request_completed(client):
    req_id = _new_request(client)
    client.post(f"/requests/{req_id}/call")  # there must be a call first

    resp = client.post(f"/requests/{req_id}/report")
    assert resp.status_code == 201
    body = resp.json()
    assert body["outcome"] == "no_rep_reached"
    assert body["summary"].startswith("No human reached")

    # The request is now completed.
    assert client.get(f"/requests/{req_id}").json()["status"] == "completed"


def test_report_without_a_call_is_rejected(client):
    req_id = _new_request(client)
    resp = client.post(f"/requests/{req_id}/report")
    assert resp.status_code == 400


def test_report_on_missing_request_is_404(client):
    assert client.post("/requests/999/report").status_code == 404


def test_get_report_returns_404_then_the_report(client):
    req_id = _new_request(client)
    client.post(f"/requests/{req_id}/call")

    # Before generating, there is no report.
    assert client.get(f"/requests/{req_id}/report").status_code == 404

    client.post(f"/requests/{req_id}/report")  # generate it

    # Now it can be fetched.
    got = client.get(f"/requests/{req_id}/report")
    assert got.status_code == 200
    assert got.json()["outcome"] == "no_rep_reached"
