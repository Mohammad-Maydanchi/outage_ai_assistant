"""Database layer for outage requests (Phase 1).

All reading/writing of outage requests goes through here, on top of the thin
SQLite connection in db.py. Keeping it in one place means swapping SQLite for
Postgres later touches mostly this file.
"""

from datetime import datetime

from app.db import get_connection
from app.extraction import ReportData
from app.models import Call, OutageRequest, OutageRequestCreate, Report

# A call in one of these states is finished; anything else is still "active".
TERMINAL_CALL_STATUSES = {"ended", "failed", "canceled", "no-answer"}

# How far along a call is — used so a late/out-of-order update can't rewind it.
STATUS_ORDER = {
    "queued": 0,
    "ringing": 1,
    "in-progress": 2,
    "ended": 3,
    "failed": 3,
    "canceled": 3,
    "no-answer": 3,
}

_CREATE_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS outage_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isp_phone TEXT NOT NULL,
    account_number TEXT NOT NULL,
    pin TEXT NOT NULL,
    business_name TEXT NOT NULL,
    business_address TEXT NOT NULL,
    isp_name TEXT,
    caller_name TEXT,
    location_phone TEXT,
    circuit_id TEXT,
    symptoms TEXT,
    troubleshooting_done TEXT,
    modem_light_status TEXT,
    use_equipment_checked_opening INTEGER NOT NULL DEFAULT 0,
    callback_number TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

# Columns added after the first version — applied to existing databases so we
# never lose data when the schema grows. (Simple POC-style migration.)
_ADDED_COLUMNS = {
    "caller_name": "TEXT",
    "location_phone": "TEXT",
    "circuit_id": "TEXT",
}

_CREATE_CALLS_TABLE = """
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    provider_call_id TEXT UNIQUE,
    status TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    duration_seconds INTEGER,
    recording_url TEXT,
    transcript TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (request_id) REFERENCES outage_requests(id)
)
"""

_CREATE_STATUS_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS call_status_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    provider_event_id TEXT UNIQUE,
    occurred_at TEXT,
    received_at TEXT NOT NULL,
    FOREIGN KEY (call_id) REFERENCES calls(id)
)
"""

_CREATE_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    responder TEXT NOT NULL,
    outage_reason TEXT,
    estimated_restoration TEXT,
    reference_ticket TEXT,
    spoke_with TEXT,
    summary TEXT,
    needs_review INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (call_id) REFERENCES calls(id)
)
"""


def init_db() -> None:
    """Create the database tables if they do not exist yet, and add any new columns."""
    conn = get_connection()
    conn.execute(_CREATE_REQUESTS_TABLE)
    conn.execute(_CREATE_CALLS_TABLE)
    conn.execute(_CREATE_STATUS_EVENTS_TABLE)
    conn.execute(_CREATE_REPORTS_TABLE)

    # Add columns that older databases may be missing.
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(outage_requests)")}
    for column, col_type in _ADDED_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE outage_requests ADD COLUMN {column} {col_type}")

    conn.commit()
    conn.close()


def _row_to_request(row) -> OutageRequest:
    """Turn a database row into an OutageRequest model."""
    return OutageRequest(
        id=row["id"],
        isp_phone=row["isp_phone"],
        account_number=row["account_number"],
        pin=row["pin"],
        business_name=row["business_name"],
        business_address=row["business_address"],
        isp_name=row["isp_name"],
        caller_name=row["caller_name"],
        location_phone=row["location_phone"],
        circuit_id=row["circuit_id"],
        symptoms=row["symptoms"],
        troubleshooting_done=row["troubleshooting_done"],
        modem_light_status=row["modem_light_status"],
        use_equipment_checked_opening=bool(row["use_equipment_checked_opening"]),
        callback_number=row["callback_number"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_request(data: OutageRequestCreate) -> OutageRequest:
    """Save a new outage request and return it (with id + timestamps filled in)."""
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO outage_requests (
            isp_phone, account_number, pin, business_name, business_address,
            isp_name, caller_name, location_phone, circuit_id, symptoms, troubleshooting_done,
            modem_light_status, use_equipment_checked_opening, callback_number,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.isp_phone,
            data.account_number,
            data.pin,
            data.business_name,
            data.business_address,
            data.isp_name,
            data.caller_name,
            data.location_phone,
            data.circuit_id,
            data.symptoms,
            data.troubleshooting_done,
            data.modem_light_status,
            int(data.use_equipment_checked_opening),
            data.callback_number,
            "new",
            now,
            now,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return get_request(new_id)


def list_requests() -> list[OutageRequest]:
    """Return all saved requests, newest first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM outage_requests ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [_row_to_request(r) for r in rows]


def get_request(request_id: int) -> OutageRequest | None:
    """Return one request by id, or None if it does not exist."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM outage_requests WHERE id = ?", (request_id,)
    ).fetchone()
    conn.close()
    return _row_to_request(row) if row else None


def set_request_status(request_id: int, status: str) -> None:
    """Update a request's status (e.g. 'new' -> 'calling')."""
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        "UPDATE outage_requests SET status = ?, updated_at = ? WHERE id = ?",
        (status, now, request_id),
    )
    conn.commit()
    conn.close()


# ----- calls -----

def _row_to_call(row) -> Call:
    return Call(
        id=row["id"],
        request_id=row["request_id"],
        provider_call_id=row["provider_call_id"],
        status=row["status"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        duration_seconds=row["duration_seconds"],
        recording_url=row["recording_url"],
        transcript=row["transcript"],
        created_at=row["created_at"],
    )


def create_call(request_id: int, provider_call_id: str, status: str) -> Call:
    """Record a new call attempt for a request."""
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO calls (request_id, provider_call_id, status, started_at, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (request_id, provider_call_id, status, now, now),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return get_call(new_id)


def get_call(call_id: int) -> Call | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
    conn.close()
    return _row_to_call(row) if row else None


def get_call_by_provider_id(provider_call_id: str) -> Call | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM calls WHERE provider_call_id = ?", (provider_call_id,)
    ).fetchone()
    conn.close()
    return _row_to_call(row) if row else None


def create_status_event(
    call_id: int, status: str, source: str, provider_event_id: str, occurred_at: str | None
) -> bool:
    """Log a status event. Returns True if newly inserted, False if a duplicate."""
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO call_status_events
            (call_id, status, source, provider_event_id, occurred_at, received_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (call_id, status, source, provider_event_id, occurred_at, now),
    )
    conn.commit()
    inserted = cursor.rowcount > 0
    conn.close()
    return inserted


def advance_call_status(call_id: int, status: str) -> None:
    """Move a call's status forward only — never backward (out-of-order safe)."""
    call = get_call(call_id)
    if call is None:
        return
    new_rank = STATUS_ORDER.get(status, -1)
    current_rank = STATUS_ORDER.get(call.status, -1)
    if new_rank < current_rank:
        return  # an older/late update — ignore
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute("UPDATE calls SET status = ? WHERE id = ?", (status, call_id))
    if status in TERMINAL_CALL_STATUSES:
        conn.execute("UPDATE calls SET ended_at = ? WHERE id = ?", (now, call_id))
    conn.commit()
    conn.close()


def get_latest_call_for_request(request_id: int) -> Call | None:
    """Return the most recent call for a request (any status), or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM calls WHERE request_id = ? ORDER BY id DESC LIMIT 1",
        (request_id,),
    ).fetchone()
    conn.close()
    return _row_to_call(row) if row else None


def record_call_result(
    call_id: int,
    status: str,
    transcript: str | None,
    duration_seconds: int | None = None,
    recording_url: str | None = None,
) -> Call:
    """Store the outcome of a call (transcript, status, etc.)."""
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        """
        UPDATE calls
        SET status = ?, transcript = ?, duration_seconds = ?, recording_url = ?, ended_at = ?
        WHERE id = ?
        """,
        (status, transcript, duration_seconds, recording_url, now, call_id),
    )
    conn.commit()
    conn.close()
    return get_call(call_id)


def get_active_call_for_request(request_id: int) -> Call | None:
    """Return an in-progress call for this request, if any (for the double-call guard)."""
    placeholders = ",".join("?" for _ in TERMINAL_CALL_STATUSES)
    conn = get_connection()
    row = conn.execute(
        f"""
        SELECT * FROM calls
        WHERE request_id = ? AND status NOT IN ({placeholders})
        ORDER BY id DESC LIMIT 1
        """,
        (request_id, *TERMINAL_CALL_STATUSES),
    ).fetchone()
    conn.close()
    return _row_to_call(row) if row else None


# ----- reports -----

def _row_to_report(row) -> Report:
    return Report(
        id=row["id"],
        call_id=row["call_id"],
        outcome=row["outcome"],
        responder=row["responder"],
        outage_reason=row["outage_reason"],
        estimated_restoration=row["estimated_restoration"],
        reference_ticket=row["reference_ticket"],
        spoke_with=row["spoke_with"],
        summary=row["summary"],
        needs_review=bool(row["needs_review"]),
        created_at=row["created_at"],
    )


def create_report(call_id: int, data: ReportData) -> Report:
    """Save a structured report for a call."""
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO reports (
            call_id, outcome, responder, outage_reason, estimated_restoration,
            reference_ticket, spoke_with, summary, needs_review, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            call_id,
            data.outcome,
            data.responder,
            data.outage_reason,
            data.estimated_restoration,
            data.reference_ticket,
            data.spoke_with,
            data.summary,
            int(data.needs_review),
            now,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return get_report(new_id)


def get_report(report_id: int) -> Report | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    return _row_to_report(row) if row else None


def get_report_for_call(call_id: int) -> Report | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports WHERE call_id = ? ORDER BY id DESC LIMIT 1", (call_id,)
    ).fetchone()
    conn.close()
    return _row_to_report(row) if row else None
