"""Tests for the ticket intake/dispatch flow, run against the Stub + fakes.

No database and no real calls: create_request and start_call are injected
fakes, so we can prove the flow logic (first response, dispatch, dedupe,
write-back, escalation) on its own.
"""

from app.extraction import ReportData
from app.ticketing.service import (
    FIRST_RESPONSE_COMMENT,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_NEEDS_HUMAN,
    TicketIntakeService,
    format_report_comment,
)
from app.ticketing.stub import OUTAGE_CATEGORY, StubTicketSource


class _FakeRecord:
    def __init__(self, id, payload):
        self.id = id
        self.payload = payload


def _make_service(source):
    created, started = [], []

    def create_request(payload):
        rec = _FakeRecord(len(created) + 1, payload)
        created.append(rec)
        return rec

    def start_call(record):
        started.append(record.id)

    svc = TicketIntakeService(
        source,
        create_request=create_request,
        start_call=start_call,
        category=OUTAGE_CATEGORY,
        caller_name="John Doe",
    )
    return svc, created, started


def test_poll_dispatches_and_posts_first_response():
    source = StubTicketSource()
    svc, created, started = _make_service(source)

    results = svc.poll_and_dispatch()

    assert len(results) == 1 and results[0].dispatched
    assert len(created) == 1  # a request was created from the ticket
    assert started == [1]  # the call was dispatched
    # First response posted + ticket moved to pause the SLA clock.
    assert source.posted_comments[0][1] == FIRST_RESPONSE_COMMENT
    assert ("75465", STATUS_IN_PROGRESS) in source.status_updates


def test_same_ticket_is_never_dispatched_twice():
    source = StubTicketSource()
    svc, created, started = _make_service(source)

    svc.poll_and_dispatch()
    second = svc.poll_and_dispatch()  # poll again — ticket still open

    assert second[0].dispatched is False
    assert second[0].skipped_reason == "already handled"
    assert len(created) == 1 and started == [1]  # not dispatched twice


def test_post_report_clear_outcome_posts_findings_and_marks_done():
    source = StubTicketSource()
    svc, *_ = _make_service(source)
    svc.poll_and_dispatch()
    source.posted_comments.clear()
    source.status_updates.clear()

    report = ReportData(
        outcome="no_outage_found",
        responder="human",
        spoke_with="Claire",
        summary="Rep checked the outage map; no known outage at the location.",
    )
    svc.post_report("75465", report)

    body = source.posted_comments[0][1]
    assert "No outage found" in body
    assert "No outage reported" in body  # reason reads sensibly for no-outage
    assert ("75465", STATUS_DONE) in source.status_updates


def test_post_report_needs_review_escalates_to_a_human():
    source = StubTicketSource()
    svc, *_ = _make_service(source)
    svc.poll_and_dispatch()
    source.status_updates.clear()

    report = ReportData(
        outcome="needs_review", responder="unknown", needs_review=True,
        summary="Call was unclear.",
    )
    svc.post_report("75465", report)

    body = source.posted_comments[-1][1]
    assert "NEEDS HUMAN REVIEW" in body
    assert ("75465", STATUS_NEEDS_HUMAN) in source.status_updates


def test_format_report_comment_no_outage_reads_sensibly():
    report = ReportData(outcome="no_outage_found", responder="human", spoke_with="Claire")
    body = format_report_comment(report)
    assert "Outage reason: No outage reported" in body
    assert "Estimated restoration: —" in body
