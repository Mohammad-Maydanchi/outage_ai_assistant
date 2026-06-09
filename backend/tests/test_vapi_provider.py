"""Phase 7 — TDD: the real Vapi provider's logic (no live network)."""

import pytest

import pytest

from app.config import settings
from app.voice import vapi as vapi_module
from app.voice.vapi import VapiVoiceProvider


def test_verify_webhook_checks_shared_secret(monkeypatch):
    monkeypatch.setattr(settings, "vapi_webhook_secret", "s3cret")
    provider = VapiVoiceProvider(api_key="k")
    assert provider.verify_webhook({"x-vapi-secret": "s3cret"}, b"{}") is True
    assert provider.verify_webhook({"x-vapi-secret": "wrong"}, b"{}") is False
    assert provider.verify_webhook({}, b"{}") is False


def test_parse_status_update():
    provider = VapiVoiceProvider(api_key="k")
    body = {
        "message": {
            "type": "status-update",
            "status": "ringing",
            "id": "evt-1",
            "call": {"id": "vapi-abc"},
        }
    }
    event = provider.parse_webhook({}, body)
    assert event.provider_call_id == "vapi-abc"
    assert event.status == "ringing"
    assert event.provider_event_id == "evt-1"


def test_parse_end_of_call_report_pulls_transcript():
    provider = VapiVoiceProvider(api_key="k")
    body = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "vapi-abc"},
            "artifact": {"transcript": "AI: hi\nUser: outage"},
        }
    }
    event = provider.parse_webhook({}, body)
    assert event.status == "ended"
    assert event.raw["transcript"] == "AI: hi\nUser: outage"


class _FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_start_call_posts_and_returns_id(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({"id": "vapi-xyz", "status": "queued"})

    monkeypatch.setattr(vapi_module.httpx, "post", fake_post)
    provider = VapiVoiceProvider(api_key="k", phone_number_id="pn-1", assistant_id="as-1")

    started = provider.start_call(
        {"destination_number": "+18002882020", "variables": {"business_name": "Vivant"}}
    )
    assert started.provider_call_id == "vapi-xyz"
    assert captured["url"].endswith("/call")
    assert captured["json"]["customer"]["number"] == "+18002882020"
    assert captured["json"]["assistantOverrides"]["variableValues"]["business_name"] == "Vivant"


def test_start_call_raises_clear_error_when_vapi_rejects(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse({"message": "Daily limit reached"}, status_code=400)

    monkeypatch.setattr(vapi_module.httpx, "post", fake_post)
    provider = VapiVoiceProvider(api_key="k", phone_number_id="pn", assistant_id="as")

    with pytest.raises(RuntimeError) as exc:
        provider.start_call({"destination_number": "+1", "variables": {}})
    assert "Daily limit reached" in str(exc.value)
