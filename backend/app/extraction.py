"""Turn a call transcript into a clean, structured report (Phase 5).

The golden rule: never fabricate. Anything not actually said in the transcript
is reported as "not provided". If the call is too unclear, the report is
flagged needs_review for a human.

The Claude call is hidden behind the Extractor interface so the rest of the app
(and the tests) don't depend on a live API.
"""

import json
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

from app.config import settings

NOT_PROVIDED = "not provided"

# What the call ended up showing.
OUTCOMES = {
    "outage_confirmed_with_eta",
    "outage_confirmed_no_eta",
    "no_outage_found",
    "equipment_issue",
    "no_rep_reached",
    "needs_review",
}

RESPONDERS = {"recorded_message", "bot", "human", "unknown"}


class ReportData(BaseModel):
    """The structured report pulled from a transcript."""

    outcome: str
    responder: str
    outage_reason: str = NOT_PROVIDED
    estimated_restoration: str = NOT_PROVIDED  # verbatim ETA, or "not provided"
    reference_ticket: str = NOT_PROVIDED
    spoke_with: str = NOT_PROVIDED
    summary: str = ""
    needs_review: bool = False


EXTRACTION_SYSTEM_PROMPT = (
    "You read a phone-call transcript between an automated agent and an ISP "
    "(its IVR, bot, or a human rep) about a possible internet outage. Extract a "
    "structured report.\n\n"
    "CRITICAL RULES:\n"
    "- NEVER invent or guess. If something was not clearly stated, use exactly "
    '"not provided".\n'
    "- Do not assume an ETA, reason, or ticket number that was not said.\n"
    "- If the call is too unclear to judge the outcome, set needs_review to true.\n"
    "- Write numbers, times, and dates as DIGITS, not spelled-out words "
    '(e.g., "7 PM" not "seven PM"; "75234" not "seven five two three four").\n\n'
    "Reply with ONLY a JSON object (no prose, no code fences) with these keys:\n"
    '  outcome: one of ["outage_confirmed_with_eta", "outage_confirmed_no_eta", '
    '"no_outage_found", "equipment_issue", "no_rep_reached", "needs_review"]\n'
    '  responder: one of ["recorded_message", "bot", "human", "unknown"]\n'
    '  outage_reason: string or "not provided"\n'
    '  estimated_restoration: the ETA verbatim, or "not provided"\n'
    '  reference_ticket: string or "not provided"\n'
    '  spoke_with: who/what was reached (rep name / "automated message"), or "not provided"\n'
    "  summary: a short, faithful 1-3 sentence summary\n"
    "  needs_review: true/false\n"
)


def build_user_prompt(transcript: str) -> str:
    return f"Here is the call transcript:\n\n{transcript}\n\nReturn the JSON report."


def _coerce(raw: dict, key: str) -> str:
    """Return a clean string for a field, defaulting to 'not provided'."""
    value = raw.get(key)
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return NOT_PROVIDED
    return str(value).strip()


def normalize_report(raw: dict) -> ReportData:
    """Apply the safety rules to whatever the model returned."""
    outcome = str(raw.get("outcome", "")).strip()
    responder = str(raw.get("responder", "")).strip()
    needs_review = bool(raw.get("needs_review", False))

    # Unknown/blank outcome is never guessed — it becomes a review item.
    if outcome not in OUTCOMES:
        outcome = "needs_review"
        needs_review = True
    if outcome == "needs_review":
        needs_review = True
    if responder not in RESPONDERS:
        responder = "unknown"

    return ReportData(
        outcome=outcome,
        responder=responder,
        outage_reason=_coerce(raw, "outage_reason"),
        estimated_restoration=_coerce(raw, "estimated_restoration"),
        reference_ticket=_coerce(raw, "reference_ticket"),
        spoke_with=_coerce(raw, "spoke_with"),
        summary=raw.get("summary", "").strip() if isinstance(raw.get("summary"), str) else "",
        needs_review=needs_review,
    )


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of the model's reply (tolerates stray text/fences)."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model reply")
    return json.loads(text[start : end + 1])


class Extractor(ABC):
    @abstractmethod
    def extract(self, transcript: str) -> ReportData:
        """Produce a structured report from a transcript."""


class ClaudeExtractor(Extractor):
    """Real extractor — asks Claude Sonnet to read the transcript."""

    MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: Optional[str] = None):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key or settings.anthropic_api_key)

    def extract(self, transcript: str) -> ReportData:
        message = self._client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": EXTRACTION_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": build_user_prompt(transcript)}],
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        return normalize_report(_extract_json(text))


class StubExtractor(Extractor):
    """Fake extractor for tests/local dev — returns a fixed report, no API."""

    def __init__(self, report: Optional[ReportData] = None):
        self._report = report or ReportData(
            outcome="needs_review", responder="unknown", needs_review=True,
            summary="(stub report)",
        )

    def extract(self, transcript: str) -> ReportData:
        return self._report


def get_extractor() -> Extractor:
    """The extractor the app uses by default (real Claude). Overridable in tests."""
    return ClaudeExtractor()
