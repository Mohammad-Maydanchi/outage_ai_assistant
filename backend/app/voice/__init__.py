"""Voice provider layer.

Everything about *placing a call* and *understanding what came back* lives
behind the VoiceProvider interface, so the rest of the app never depends on a
specific vendor (Vapi today, Bland AI possible later).
"""

from app.config import settings
from app.voice.base import VoiceProvider
from app.voice.stub import StubVoiceProvider
from app.voice.vapi import VapiVoiceProvider

# The fake provider (no real calls, no cost) is the default. As soon as a
# VAPI_API_KEY is set in .env, the app uses the real Vapi provider instead.
_stub = StubVoiceProvider()


def get_voice_provider() -> VoiceProvider:
    if settings.vapi_api_key:
        return VapiVoiceProvider()
    return _stub
