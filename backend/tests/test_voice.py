"""Phase 3 — TDD: the call payload builder and the fake voice provider."""

from datetime import datetime

from app.models import OutageRequest
from app.voice.payload import build_call_payload
from app.voice.stub import StubVoiceProvider


def _request(**overrides) -> OutageRequest:
    base = dict(
        id=1,
        isp_phone="18005551234",
        account_number="1234567890",
        pin="4321",
        business_name="Vivant Corp",
        business_address="2727 Lyndon, 75234",
        isp_name="AT&T",
        status="new",
        created_at=datetime(2026, 5, 29),
        updated_at=datetime(2026, 5, 29),
    )
    base.update(overrides)
    return OutageRequest(**base)


def test_payload_has_destination_and_business_variables():
    payload = build_call_payload(_request())
    assert payload["destination_number"] == "18005551234"
    assert payload["variables"]["business_name"] == "Vivant Corp"
    assert payload["variables"]["account_number"] == "1234567890"  # full, for the call


def test_payload_carries_caller_name_and_location_phone():
    payload = build_call_payload(
        _request(caller_name="Hmed Mazerwe", location_phone="4692570077")
    )
    assert payload["variables"]["caller_name"] == "Hmed Mazerwe"
    assert payload["variables"]["location_phone"] == "4692570077"


def test_payload_includes_att_hint_and_rules():
    payload = build_call_payload(_request(isp_name="AT&T"))
    assert "technical support representative" in payload["isp_hint"]
    # The rules now cover both machine (brief) and human (natural) tone.
    assert any("human" in rule.lower() for rule in payload["agent_rules"])


def test_payload_opening_toggle_off_by_default():
    payload = build_call_payload(_request(use_equipment_checked_opening=False))
    assert payload["optional_opening"] == ""
    payload_on = build_call_payload(_request(use_equipment_checked_opening=True))
    assert "already checked" in payload_on["optional_opening"]


def test_stub_start_call_returns_id_and_remembers_payload():
    provider = StubVoiceProvider()
    payload = build_call_payload(_request())
    started = provider.start_call(payload)
    assert started.provider_call_id.startswith("stub-call-")
    assert started.status == "queued"
    assert provider.last_payload == payload


def test_stub_implements_the_full_contract():
    provider = StubVoiceProvider()
    event = provider.parse_webhook({}, {"event_id": "e1", "status": "ringing"})
    assert event.status == "ringing"
    snapshot = provider.fetch_call("stub-call-1")
    assert snapshot.status == "ended"
    assert provider.get_structured_output("stub-call-1") is None
