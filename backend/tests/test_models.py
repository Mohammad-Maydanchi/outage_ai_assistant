"""Phase 1 — TDD: the request model validates required fields and the
public view masks secrets (account number + PIN)."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    OutageRequest,
    OutageRequestCreate,
    OutageRequestPublic,
    mask_secret,
)


def test_mask_account_shows_only_last_4():
    assert mask_secret("1234567890") == "••••7890"


def test_mask_short_pin_is_fully_hidden():
    # A 4-digit PIN must not be revealed by "show last 4".
    assert mask_secret("4321") == "••••"


def test_required_fields_must_be_filled():
    with pytest.raises(ValidationError):
        OutageRequestCreate(
            isp_phone="",
            account_number="",
            pin="",
            business_name="",
            business_address="",
        )


def test_valid_request_is_accepted():
    req = OutageRequestCreate(
        isp_phone="18005551234",
        account_number="1234567890",
        pin="4321",
        business_name="Vivant Corp",
        business_address="2727 Lyndon, 75234",
    )
    assert req.business_name == "Vivant Corp"
    assert req.use_equipment_checked_opening is False  # default off


def test_public_view_masks_secrets_but_keeps_normal_fields():
    record = OutageRequest(
        id=1,
        isp_phone="18005551234",
        account_number="1234567890",
        pin="4321",
        business_name="Vivant Corp",
        business_address="2727 Lyndon, 75234",
        status="new",
        created_at=datetime(2026, 5, 29),
        updated_at=datetime(2026, 5, 29),
    )
    public = OutageRequestPublic.from_record(record)
    assert public.account_number == "••••7890"  # masked
    assert public.pin == "••••"  # fully hidden
    assert public.business_name == "Vivant Corp"  # normal field untouched
