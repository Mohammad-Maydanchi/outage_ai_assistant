"""Phase 1 — TDD: saving, listing, and fetching outage requests from SQLite.

Each test runs against a fresh temporary database so it never touches the
real outage.db.
"""

import pytest

from app import repository
from app.config import settings
from app.models import OutageRequestCreate


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the app at a brand-new empty database file for this test."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_file}")
    repository.init_db()
    yield


def _sample(name="Vivant Corp"):
    return OutageRequestCreate(
        isp_phone="18005551234",
        account_number="1234567890",
        pin="4321",
        business_name=name,
        business_address="2727 Lyndon, 75234",
    )


def test_create_then_get_returns_same_request(temp_db):
    created = repository.create_request(_sample())
    assert created.id is not None
    assert created.status == "new"  # default status
    assert created.created_at is not None

    fetched = repository.get_request(created.id)
    assert fetched is not None
    assert fetched.business_name == "Vivant Corp"
    # In the database the secret is stored in full (masking happens only in the UI view).
    assert fetched.account_number == "1234567890"


def test_list_returns_all_saved_newest_first(temp_db):
    repository.create_request(_sample(name="First"))
    repository.create_request(_sample(name="Second"))

    items = repository.list_requests()
    assert len(items) == 2
    assert items[0].business_name == "Second"  # newest first


def test_get_missing_returns_none(temp_db):
    assert repository.get_request(999) is None
