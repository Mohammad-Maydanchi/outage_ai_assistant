"""The TicketSource interface — the standard "plug" for the ticketing system.

The app only ever talks to this interface. A real backend (Utiliko) and a fake
one (Stub) both implement it, so they are interchangeable — exactly the same
pattern the app already uses for voice (see app/voice/base.py). This lets us
build and test the whole ticket -> call -> report -> write-back flow against
fake data now, before Utiliko's real API details are confirmed.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TicketRef:
    """A lightweight reference to a ticket found while scanning the queue."""

    ticket_number: str
    category: str
    status: str
    sla_first_response_target: Optional[str] = None


@dataclass
class TicketDetail:
    """One ticket's full details, as read from the ticketing system."""

    ticket_number: str
    tenant: str
    domain: str
    category: str
    status: str
    description: str = ""
    sla_first_response_target: Optional[str] = None  # per-ticket SLA deadline
    raw: dict = field(default_factory=dict)


@dataclass
class Company:
    """The client/company a ticket belongs to."""

    name: str = ""
    address: str = ""
    phone: str = ""


@dataclass
class IspInfo:
    """The ISP/service details needed to place and verify the call.

    Mirrors Utiliko's client "ISP Info" tab. Any field can be blank — a blank
    PIN/account is reported as "couldn't verify", never invented.
    """

    isp_name: str = ""
    account_or_circuit_id: str = ""  # one combined field in Utiliko
    support_phone: str = ""  # the ISP number to dial
    pin: str = ""  # may be blank on the real record
    circuit_type: str = ""
    service_address: str = ""
    callback_number: str = ""


@dataclass
class CommentRef:
    """Result of posting a comment/note back to a ticket."""

    ticket_number: str
    comment_id: str


class TicketSource(ABC):
    """Every ticketing backend must provide these abilities."""

    @abstractmethod
    def list_open_outage_tickets(
        self, category: str, since: Optional[str] = None
    ) -> list[TicketRef]:
        """Return open tickets in the given outage category (newest first)."""

    @abstractmethod
    def fetch_ticket(self, ticket_number: str) -> TicketDetail:
        """Read one ticket's full details by its number."""

    @abstractmethod
    def fetch_company(self, tenant: str, domain: str) -> Company:
        """Resolve the client/company a ticket belongs to."""

    @abstractmethod
    def fetch_isp_info(self, tenant: str, domain: str) -> IspInfo:
        """Read the client's ISP info (account #, PIN, support phone, address)."""

    @abstractmethod
    def post_comment(
        self, ticket_number: str, body: str, internal: bool = False
    ) -> CommentRef:
        """Post a comment/note back on the ticket."""

    @abstractmethod
    def update_status(self, ticket_number: str, status: str) -> None:
        """Change the ticket's status (used to claim it and to pause the SLA)."""
