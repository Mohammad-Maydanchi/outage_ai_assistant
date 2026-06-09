"""Phase 0 — TDD: the app must boot and expose a working health check
that also confirms the SQLite database is reachable."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_health_reports_database_connected():
    resp = client.get("/health")
    body = resp.json()
    # Phase 0 requires proving the DB connection works, not just that the app boots.
    assert body["database"] == "connected"
