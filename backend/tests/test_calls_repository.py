"""Phase 3 — TDD: storing call attempts and finding active calls."""

import pytest

from app import repository
from app.config import settings
from app.models import OutageRequestCreate


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_file}")
    repository.init_db()
    yield


def _make_request():
    return repository.create_request(
        OutageRequestCreate(
            isp_phone="18005551234",
            account_number="1234567890",
            pin="4321",
            business_name="Vivant Corp",
            business_address="2727 Lyndon, 75234",
        )
    )


def test_create_and_get_call(temp_db):
    req = _make_request()
    call = repository.create_call(req.id, "stub-call-1", "queued")
    assert call.id is not None
    assert call.request_id == req.id
    assert call.provider_call_id == "stub-call-1"
    assert call.status == "queued"


def test_active_call_is_found_while_in_progress(temp_db):
    req = _make_request()
    repository.create_call(req.id, "stub-call-1", "queued")
    active = repository.get_active_call_for_request(req.id)
    assert active is not None
    assert active.provider_call_id == "stub-call-1"


def test_finished_call_is_not_active(temp_db):
    req = _make_request()
    repository.create_call(req.id, "stub-call-1", "ended")
    assert repository.get_active_call_for_request(req.id) is None


def test_set_request_status(temp_db):
    req = _make_request()
    repository.set_request_status(req.id, "calling")
    assert repository.get_request(req.id).status == "calling"
