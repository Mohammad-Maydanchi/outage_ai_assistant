"""Shared test setup.

Tests must never depend on real API keys in .env or make real phone calls.
Forcing the Vapi key empty makes get_voice_provider() return the fake (stub)
provider for every test. (Tests that exercise the real Vapi provider construct
it directly with an explicit key, so they are unaffected.)
"""

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _force_stub_provider(monkeypatch):
    monkeypatch.setattr(settings, "vapi_api_key", "")
