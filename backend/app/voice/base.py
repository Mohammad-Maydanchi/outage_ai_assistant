"""The VoiceProvider interface — the standard "plug" every voice vendor fills.

The app only ever talks to this interface. A real vendor (Vapi) and a fake one
(Stub) both implement it, so they are interchangeable.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StartedCall:
    """Result of asking the provider to start a call."""

    provider_call_id: str
    status: str


@dataclass
class NormalizedEvent:
    """A status update from the provider, translated into our own shape."""

    provider_event_id: str
    status: str
    provider_call_id: Optional[str] = None
    occurred_at: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class CallSnapshot:
    """The current state of a call when we ask the provider directly."""

    provider_call_id: str
    status: str
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    duration_seconds: Optional[int] = None


class VoiceProvider(ABC):
    """Every voice vendor must provide these four abilities."""

    @abstractmethod
    def start_call(self, payload: dict) -> StartedCall:
        """Place an outbound call from a prepared payload."""

    @abstractmethod
    def verify_webhook(self, headers: dict, raw_body: bytes) -> bool:
        """True if this webhook request genuinely came from the provider."""

    @abstractmethod
    def parse_webhook(self, headers: dict, body: dict) -> NormalizedEvent:
        """Turn a raw vendor webhook into our normalized event."""

    @abstractmethod
    def fetch_call(self, provider_call_id: str) -> CallSnapshot:
        """Ask the vendor for the current state of a call."""

    @abstractmethod
    def get_structured_output(self, provider_call_id: str) -> Optional[dict]:
        """Return the vendor's structured analysis of the call, if any."""
