"""Tests for the ticketing layer (built against the Stub, no real Utiliko)."""

from app.models import OutageRequestCreate
from app.ticketing import get_ticket_source
from app.ticketing.base import TicketSource
from app.ticketing.mapping import map_ticket_to_request
from app.ticketing.stub import OUTAGE_CATEGORY, StubTicketSource


def test_factory_returns_a_ticket_source():
    assert isinstance(get_ticket_source(), TicketSource)


def test_list_open_outage_tickets_only_returns_that_category():
    src = StubTicketSource()
    tickets = src.list_open_outage_tickets(OUTAGE_CATEGORY)
    assert tickets, "stub should have at least one open outage ticket"
    assert all(t.category == OUTAGE_CATEGORY for t in tickets)


def test_fetch_ticket_returns_tenant_domain_and_notes():
    src = StubTicketSource()
    ticket = src.fetch_ticket("75465")
    assert ticket.tenant == "Vivant Corp"
    assert ticket.domain
    assert "DOWN" in ticket.description.upper()


def test_mapping_builds_a_valid_request_and_never_invents_a_blank_pin():
    src = StubTicketSource()
    ticket = src.fetch_ticket("75465")
    company = src.fetch_company(ticket.tenant, ticket.domain)
    isp = src.fetch_isp_info(ticket.tenant, ticket.domain)

    req = map_ticket_to_request(ticket, company, isp, caller_name="John Doe")

    assert isinstance(req, OutageRequestCreate)
    assert req.isp_phone == "8003147195"  # the number to dial
    assert req.account_number == "8141400090147054"
    assert req.pin == ""  # blank on the record — passed through, not fabricated
    assert req.business_name == "Vivant Corp"
    assert req.business_address  # filled from the ISP service address
    assert req.caller_name == "John Doe"
    assert req.symptoms  # context carried from the ticket


def test_posting_comment_and_status_are_recorded():
    src = StubTicketSource()
    ref = src.post_comment("75465", "Automated outage check started.")
    assert ref.comment_id
    src.update_status("75465", "In Progress")
    assert ("75465", "In Progress") in src.status_updates
    assert src.posted_comments[0][0] == "75465"
