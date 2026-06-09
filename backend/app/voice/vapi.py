"""The real Vapi voice provider.

Implements the same VoiceProvider interface as the stub, so it slots straight
into the app. Used automatically once a VAPI_API_KEY is set in .env.

API reference: https://docs.vapi.ai/api-reference/calls/create
Webhooks:      https://docs.vapi.ai/server-url/events
"""

import httpx

from app.config import settings
from app.voice.base import CallSnapshot, NormalizedEvent, StartedCall, VoiceProvider

# Map Vapi's call statuses onto the ones our app tracks.
_STATUS_MAP = {
    "scheduled": "queued",
    "queued": "queued",
    "ringing": "ringing",
    "in-progress": "in-progress",
    "forwarding": "in-progress",
    "ended": "ended",
}


def _normalize_status(status: str) -> str:
    return _STATUS_MAP.get(status, status)


class VapiVoiceProvider(VoiceProvider):
    BASE_URL = "https://api.vapi.ai"

    def __init__(self, api_key=None, phone_number_id=None, assistant_id=None):
        self._api_key = api_key or settings.vapi_api_key
        self._phone_number_id = phone_number_id or settings.vapi_phone_number_id
        self._assistant_id = assistant_id or settings.vapi_assistant_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def start_call(self, payload: dict) -> StartedCall:
        body = {
            "phoneNumberId": self._phone_number_id,
            "customer": {"number": payload["destination_number"]},
            "assistantId": self._assistant_id,
            "assistantOverrides": {
                # Dynamic variables the assistant can use in its prompt.
                "variableValues": payload.get("variables", {}),
            },
        }
        resp = httpx.post(
            f"{self.BASE_URL}/call", headers=self._headers(), json=body, timeout=30
        )
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("message") or resp.text
            except Exception:
                detail = resp.text
            raise RuntimeError(f"Vapi could not start the call ({resp.status_code}): {detail}")
        data = resp.json()
        return StartedCall(
            provider_call_id=data["id"],
            status=_normalize_status(data.get("status", "queued")),
        )

    def verify_webhook(self, headers: dict, raw_body: bytes) -> bool:
        # Vapi sends the shared secret in the X-Vapi-Secret header.
        secret = settings.vapi_webhook_secret
        return bool(secret) and headers.get("x-vapi-secret") == secret

    def parse_webhook(self, headers: dict, body: dict) -> NormalizedEvent:
        message = body.get("message", body)
        call = message.get("call") or {}
        msg_type = message.get("type", "")
        artifact = message.get("artifact") or {}

        if msg_type == "end-of-call-report":
            status = "ended"
        else:
            status = message.get("status", msg_type)

        raw = dict(message)
        if artifact.get("transcript"):
            raw["transcript"] = artifact["transcript"]

        return NormalizedEvent(
            provider_event_id=message.get("id") or f"{call.get('id')}-{msg_type}",
            status=_normalize_status(status),
            provider_call_id=call.get("id"),
            occurred_at=message.get("timestamp"),
            raw=raw,
        )

    def fetch_call(self, provider_call_id: str) -> CallSnapshot:
        resp = httpx.get(
            f"{self.BASE_URL}/call/{provider_call_id}",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        artifact = data.get("artifact") or {}
        recording = artifact.get("recording") or {}
        return CallSnapshot(
            provider_call_id=provider_call_id,
            status=_normalize_status(data.get("status", "unknown")),
            transcript=artifact.get("transcript") or data.get("transcript"),
            recording_url=recording.get("stereoUrl") or data.get("recordingUrl"),
        )

    def get_structured_output(self, provider_call_id: str) -> dict | None:
        resp = httpx.get(
            f"{self.BASE_URL}/call/{provider_call_id}",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        analysis = resp.json().get("analysis") or {}
        return analysis.get("structuredData")
