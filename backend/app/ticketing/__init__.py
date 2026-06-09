"""Ticketing layer — the ticket system (Utiliko) behind a swappable interface.

Like the voice layer, the rest of the app talks only to TicketSource. The Stub
(fake data, no real system) is the default. The real UtilikoClient takes over
once its API base URL + credentials are configured — a config change, not a
code change for the callers.
"""

from app.config import settings
from app.ticketing.base import TicketSource
from app.ticketing.stub import StubTicketSource

_stub = StubTicketSource()


def get_ticket_source() -> TicketSource:
    # Until the real Utiliko API is wired (UTILIKO_API_BASE + key), use the stub.
    # When UtilikoClient lands:
    #     if settings.utiliko_api_base and settings.utiliko_api_key:
    #         return UtilikoClient()
    return _stub
