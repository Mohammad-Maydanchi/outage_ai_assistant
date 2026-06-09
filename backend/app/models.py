"""Data models for outage requests (Phase 1).

These define the *shape* of a request and how it is validated, plus how it
looks when returned to the UI (with secrets masked). No database here — that
lives in the repository layer.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


def mask_secret(value: Optional[str], show_last: int = 4) -> str:
    """Hide a secret, revealing only the last `show_last` characters.

    If the value is short (<= show_last), hide it completely. This protects
    short secrets like a 4-digit PIN, where showing the "last 4" would reveal
    the whole thing. Example: "1234567890" -> "••••7890"; "4321" -> "••••".
    """
    value = "" if value is None else str(value)
    if len(value) <= show_last:
        return "••••"
    return "••••" + value[-show_last:]


class OutageRequestCreate(BaseModel):
    """What the user submits to create a request. Required fields must be filled."""

    # Required
    isp_phone: str = Field(min_length=1)
    account_number: str = Field(min_length=1)

    # Optional
    business_name: str = ""
    business_address: str = ""
    pin: str = ""  # stored, masked

    # Optional (help the agent)
    isp_name: Optional[str] = None
    caller_name: Optional[str] = None  # name the agent gives on the call
    location_phone: Optional[str] = None  # phone on the ISP account (IVR match)
    circuit_id: Optional[str] = None  # for ISP verification (e.g. AT&T enterprise)
    symptoms: Optional[str] = None
    troubleshooting_done: Optional[str] = None
    modem_light_status: Optional[str] = None
    use_equipment_checked_opening: bool = False
    callback_number: Optional[str] = None


class OutageRequest(OutageRequestCreate):
    """A full request as stored in the database (adds the system fields)."""

    id: int
    status: str
    created_at: datetime
    updated_at: datetime


class Call(BaseModel):
    """A single phone-call attempt for a request (Phase 3)."""

    id: int
    request_id: int
    provider_call_id: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    created_at: datetime


class Report(BaseModel):
    """A stored, structured report for a call (Phase 5)."""

    id: int
    call_id: int
    outcome: str
    responder: str
    outage_reason: str
    estimated_restoration: str
    reference_ticket: str
    spoke_with: str
    summary: str
    needs_review: bool
    created_at: datetime


class OutageRequestPublic(BaseModel):
    """A request as shown to the UI — secrets are masked here."""

    id: int
    isp_phone: str
    account_number: str  # masked
    pin: str  # masked
    business_name: str
    business_address: str
    isp_name: Optional[str] = None
    caller_name: Optional[str] = None
    location_phone: Optional[str] = None
    circuit_id: Optional[str] = None
    symptoms: Optional[str] = None
    troubleshooting_done: Optional[str] = None
    modem_light_status: Optional[str] = None
    use_equipment_checked_opening: bool = False
    callback_number: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: OutageRequest) -> "OutageRequestPublic":
        """Build the public (masked) view from a stored record."""
        data = record.model_dump()
        data["account_number"] = mask_secret(record.account_number)
        data["pin"] = mask_secret(record.pin)
        return cls(**data)
