"""Phase 5 — TDD: saving and fetching a report for a call."""

import pytest

from app import repository
from app.config import settings
from app.extraction import ReportData
from app.models import OutageRequestCreate


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_file}")
    repository.init_db()
    yield


def _call():
    req = repository.create_request(
        OutageRequestCreate(
            isp_phone="18005551234",
            account_number="1234567890",
            pin="4321",
            business_name="Vivant Corp",
            business_address="2727 Lyndon, 75234",
        )
    )
    return repository.create_call(req.id, "stub-call-1", "ended")


def test_create_and_fetch_report(temp_db):
    call = _call()
    data = ReportData(
        outcome="no_rep_reached",
        responder="bot",
        spoke_with="automated message",
        summary="No human reached; callback offered.",
        needs_review=False,
    )
    saved = repository.create_report(call.id, data)
    assert saved.id is not None
    assert saved.call_id == call.id
    assert saved.outcome == "no_rep_reached"
    assert saved.needs_review is False  # stored as bool, not 0/1

    fetched = repository.get_report_for_call(call.id)
    assert fetched is not None
    assert fetched.summary == "No human reached; callback offered."


def test_no_report_yet_returns_none(temp_db):
    call = _call()
    assert repository.get_report_for_call(call.id) is None
