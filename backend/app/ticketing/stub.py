"""A fake ticket source for tests and local development.

It talks to NO real system and costs nothing. It returns believable fixture
tickets and client data — modeled on the real Utiliko screens — so the whole
ticket -> call -> report -> write-back flow can be built and tested before the
real Utiliko API is available. Mirrors app/voice/stub.py.
"""

from app.ticketing.base import (
    Company,
    CommentRef,
    IspInfo,
    TicketDetail,
    TicketRef,
    TicketSource,
)

# The exact category string is configurable (confirm with Kartik); this is the
# value seen on the real ticket screen.
OUTAGE_CATEGORY = "ISP Service – Unplanned Outage"

# Fixture data modeled on the real Utiliko ticket + client "ISP Info" tab.
_TICKETS = {
    "75465": TicketDetail(
        ticket_number="75465",
        tenant="Vivant Corp",
        domain="vivantcorp.com",
        category=OUTAGE_CATEGORY,
        status="New",
        description=(
            "Cradlepoint NCM alert: IP Verify test 'Primary_Internet_DOWN' has "
            "failed at the site. Internet appears to be down."
        ),
        sla_first_response_target="2026-06-08T15:00:00Z",
    ),
}
_COMPANIES = {
    "Vivant Corp": Company(
        name="Vivant Corp",
        address="5722 W. Loop 1604 N., San Antonio, TX",
        phone="(123) 456-7890",
    ),
}
_ISP_INFO = {
    "Vivant Corp": IspInfo(
        isp_name="ISP-SPECT",
        account_or_circuit_id="8141400090147054",
        support_phone="8003147195",  # the number to dial
        pin="",  # blank on the real record — the agent must handle this
        circuit_type="Coax",
        service_address="5722 W. Loop 1604 N., San Antonio, TX",
        callback_number="(123) 456-7890",
    ),
}

_CLOSED_STATUSES = {"Resolved", "Closed"}


class StubTicketSource(TicketSource):
    def __init__(self):
        # Recorded for tests, so a test can assert what the agent posted.
        self.posted_comments: list[tuple[str, str, bool]] = []
        self.status_updates: list[tuple[str, str]] = []
        self._counter = 0

    def list_open_outage_tickets(self, category, since=None):
        return [
            TicketRef(
                t.ticket_number, t.category, t.status, t.sla_first_response_target
            )
            for t in _TICKETS.values()
            if t.category == category and t.status not in _CLOSED_STATUSES
        ]

    def fetch_ticket(self, ticket_number):
        return _TICKETS[ticket_number]

    def fetch_company(self, tenant, domain):
        return _COMPANIES.get(tenant, Company())

    def fetch_isp_info(self, tenant, domain):
        return _ISP_INFO.get(tenant, IspInfo())

    def post_comment(self, ticket_number, body, internal=False):
        self.posted_comments.append((ticket_number, body, internal))
        self._counter += 1
        return CommentRef(
            ticket_number=ticket_number, comment_id=f"stub-comment-{self._counter}"
        )

    def update_status(self, ticket_number, status):
        self.status_updates.append((ticket_number, status))
