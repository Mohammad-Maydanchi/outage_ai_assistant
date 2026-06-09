"""The intake/dispatch flow that ties a TicketSource to the call pipeline.

This is the heart of the integration, written entirely against the TicketSource
interface, so it runs on the Stub (fake data) now and the real UtilikoClient
later with no change. It implements the numbered flow from the architecture:

  1. detect open outage tickets
  2. read the ticket + post a first-response comment (pause the SLA clock)
  3. dispatch the call (via the injected start_call)
  ...
  9. post the report back on the ticket
  10. escalate to a human when there is no answer or the report needs review

The call placement (start_call) and the request persistence (create_request)
are injected, so this module has no database or voice dependency and is fully
testable against fakes.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from app.extraction import ReportData
from app.models import OutageRequestCreate
from app.ticketing.base import TicketSource
from app.ticketing.mapping import map_ticket_to_request

# What the agent posts the instant it picks up a ticket — this is the first
# response that is meant to pause the 60-minute SLA clock (confirm with Kartik
# which exact action stops the clock).
FIRST_RESPONSE_COMMENT = (
    "Automated outage check started. Contacting the ISP now; "
    "findings will be posted on this ticket shortly."
)

# Ticket statuses. The exact names are a question for Kartik; these match the
# statuses seen on the real board and are easy to change in one place.
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE = "Answered"  # agent posted findings, awaiting a human
STATUS_NEEDS_HUMAN = "Follow up"  # escalated: a human should take over

OUTCOME_LABELS = {
    "outage_confirmed_with_eta": "Outage confirmed (ETA given)",
    "outage_confirmed_no_eta": "Outage confirmed (no ETA)",
    "no_outage_found": "No outage found",
    "equipment_issue": "Equipment issue",
    "no_rep_reached": "Could not reach anyone",
    "needs_review": "Needs review",
}
RESPONDER_LABELS = {
    "recorded_message": "recorded message",
    "bot": "automated bot",
    "human": "human rep",
    "unknown": "unknown",
}

# Outcomes that should be handed to a human rather than closed by the agent.
_ESCALATE_OUTCOMES = {"no_rep_reached", "needs_review"}


def needs_escalation(report: ReportData) -> bool:
    """True when a human should take over (no answer, or unclear result)."""
    return report.needs_review or report.outcome in _ESCALATE_OUTCOMES


def format_report_comment(report: ReportData) -> str:
    """Turn a structured report into the comment posted back on the ticket."""
    no_outage = report.outcome == "no_outage_found"
    reason = "No outage reported" if no_outage else report.outage_reason
    eta = "—" if no_outage else report.estimated_restoration

    lines = [
        "Automated outage check — result",
        "",
        f"Outcome: {OUTCOME_LABELS.get(report.outcome, report.outcome)}",
        f"Spoke with: {RESPONDER_LABELS.get(report.responder, report.responder)}"
        f" ({report.spoke_with})",
        f"Outage reason: {reason}",
        f"Estimated restoration: {eta}",
        f"Reference / ticket #: {report.reference_ticket}",
    ]
    if report.summary:
        lines += ["", f"Summary: {report.summary}"]
    if needs_escalation(report):
        lines = ["[NEEDS HUMAN REVIEW]", ""] + lines
    return "\n".join(lines)


@dataclass
class IntakeResult:
    """What happened for one ticket during a poll."""

    ticket_number: str
    request_id: Optional[int] = None
    dispatched: bool = False
    skipped_reason: Optional[str] = None


class TicketIntakeService:
    """Detect new outage tickets and drive them through the call pipeline."""

    def __init__(
        self,
        source: TicketSource,
        *,
        create_request: Callable[[OutageRequestCreate], object],
        start_call: Callable[[object], None],
        category: str,
        caller_name: str = "",
    ):
        self.source = source
        self._create_request = create_request  # repository.create_request-like
        self._start_call = start_call  # places the call for a saved request
        self.category = category
        self.caller_name = caller_name
        # In-memory dedupe for now (one ticket = one call). The durable,
        # DB-backed version (unique utiliko_ticket_id) comes in the DB step.
        self._seen: set[str] = set()
        self._ticket_for_request: dict[int, str] = {}

    def poll_and_dispatch(self) -> list[IntakeResult]:
        """Step 1-3 + 9-prep: find open outage tickets and dispatch the new ones."""
        results = []
        for ref in self.source.list_open_outage_tickets(self.category):
            results.append(self._handle(ref.ticket_number))
        return results

    def _handle(self, ticket_number: str) -> IntakeResult:
        if ticket_number in self._seen:  # idempotent: never dispatch twice
            return IntakeResult(ticket_number, skipped_reason="already handled")

        ticket = self.source.fetch_ticket(ticket_number)
        company = self.source.fetch_company(ticket.tenant, ticket.domain)
        isp = self.source.fetch_isp_info(ticket.tenant, ticket.domain)

        payload = map_ticket_to_request(ticket, company, isp, self.caller_name)
        record = self._create_request(payload)

        # First response: post immediately + move the ticket, to pause the SLA
        # clock regardless of how long the call takes.
        self.source.post_comment(ticket_number, FIRST_RESPONSE_COMMENT)
        self.source.update_status(ticket_number, STATUS_IN_PROGRESS)

        self._seen.add(ticket_number)
        self._ticket_for_request[record.id] = ticket_number
        self._start_call(record)
        return IntakeResult(ticket_number, request_id=record.id, dispatched=True)

    def post_report(self, ticket_number: str, report: ReportData) -> None:
        """Step 9-10: post the findings back, and escalate to a human if needed."""
        self.source.post_comment(ticket_number, format_report_comment(report))
        status = STATUS_NEEDS_HUMAN if needs_escalation(report) else STATUS_DONE
        self.source.update_status(ticket_number, status)

    def ticket_for_request(self, request_id: int) -> Optional[str]:
        """Which ticket a dispatched request came from (used for the write-back)."""
        return self._ticket_for_request.get(request_id)
