"""A fake voice provider for tests and local development.

It makes NO real calls and costs nothing. It just returns believable fake
results so the rest of the app can be built and tested safely.
"""

import itertools

from app.config import settings
from app.security import verify_signature
from app.voice.base import CallSnapshot, NormalizedEvent, StartedCall, VoiceProvider
from app.voice.sample_transcripts import ATT_BASELINE


class StubVoiceProvider(VoiceProvider):
    def __init__(self):
        self._counter = itertools.count(1)
        self.last_payload: dict | None = None  # handy for tests

    def start_call(self, payload: dict) -> StartedCall:
        self.last_payload = payload
        call_id = f"stub-call-{next(self._counter)}"
        return StartedCall(provider_call_id=call_id, status="queued")

    def verify_webhook(self, headers: dict, raw_body: bytes) -> bool:
        return verify_signature(
            settings.vapi_webhook_secret, raw_body, headers.get("x-vapi-signature")
        )

    def parse_webhook(self, headers: dict, body: dict) -> NormalizedEvent:
        return NormalizedEvent(
            provider_event_id=body.get("event_id", "stub-event"),
            status=body.get("status", "unknown"),
            provider_call_id=body.get("call_id"),
            occurred_at=body.get("occurred_at"),
            raw=body,
        )

    def fetch_call(self, provider_call_id: str) -> CallSnapshot:
        # Hand back a real, messy sample call so the report pipeline can be
        # demoed end-to-end without placing a live call.
        return CallSnapshot(
            provider_call_id=provider_call_id,
            status="ended",
            transcript=ATT_BASELINE,
            duration_seconds=180,
        )

    def get_structured_output(self, provider_call_id: str) -> dict | None:
        return None
