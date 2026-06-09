"""Phase 5 — TDD: the never-fabricate report logic.

These test our own rules (normalize_report) with fixture data — no live API,
so they are free and deterministic.
"""

from app.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    NOT_PROVIDED,
    StubExtractor,
    ReportData,
    normalize_report,
)


def test_system_prompt_forbids_fabrication():
    assert "NEVER invent" in EXTRACTION_SYSTEM_PROMPT
    assert "not provided" in EXTRACTION_SYSTEM_PROMPT


def test_outage_with_eta_is_kept():
    report = normalize_report(
        {
            "outcome": "outage_confirmed_with_eta",
            "responder": "recorded_message",
            "outage_reason": "area fiber cut",
            "estimated_restoration": "by 6 PM today",
            "summary": "Recorded message reported an outage with a 6 PM ETA.",
        }
    )
    assert report.outcome == "outage_confirmed_with_eta"
    assert report.estimated_restoration == "by 6 PM today"
    assert report.needs_review is False


def test_missing_eta_becomes_not_provided():
    report = normalize_report(
        {
            "outcome": "outage_confirmed_no_eta",
            "responder": "human",
            "outage_reason": "area outage",
            # no estimated_restoration / reference_ticket given
            "summary": "Rep confirmed an outage but gave no ETA.",
        }
    )
    assert report.estimated_restoration == NOT_PROVIDED
    assert report.reference_ticket == NOT_PROVIDED


def test_no_outage_outcome():
    report = normalize_report(
        {"outcome": "no_outage_found", "responder": "human", "summary": "No outage."}
    )
    assert report.outcome == "no_outage_found"


def test_unknown_outcome_is_flagged_for_review_not_guessed():
    report = normalize_report(
        {"outcome": "??", "responder": "bot", "summary": "unclear"}
    )
    assert report.outcome == "needs_review"
    assert report.needs_review is True


def test_blank_eta_string_is_not_provided():
    report = normalize_report(
        {"outcome": "outage_confirmed_no_eta", "responder": "human",
         "estimated_restoration": "   ", "summary": "outage"}
    )
    assert report.estimated_restoration == NOT_PROVIDED


def test_stub_extractor_returns_a_report():
    out = StubExtractor().extract("any transcript")
    assert isinstance(out, ReportData)
