"""FastAPI application entry point.

Phase 0: boot the app + a /health endpoint that confirms SQLite is reachable.
Phase 1: create / list / get outage requests (secrets masked in responses).
"""

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request

from app import repository
from app.db import check_connection
from app.extraction import Extractor, get_extractor
from app.models import Call, OutageRequestCreate, OutageRequestPublic, Report
from app.voice import get_voice_provider
from app.voice.payload import build_call_payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Make sure the database table exists before the app serves requests.
    repository.init_db()
    yield


app = FastAPI(
    title="Outbound ISP Outage Voice Agent — POC",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    """Liveness + DB connectivity check."""
    db_ok = check_connection()
    return {
        "status": "ok",
        "database": "connected" if db_ok else "unavailable",
    }


@app.post("/requests", response_model=OutageRequestPublic, status_code=201)
def create_request(payload: OutageRequestCreate) -> OutageRequestPublic:
    """Save a new outage request. Returns it with secrets masked."""
    record = repository.create_request(payload)
    return OutageRequestPublic.from_record(record)


@app.get("/requests", response_model=list[OutageRequestPublic])
def list_requests() -> list[OutageRequestPublic]:
    """List all saved requests (newest first), secrets masked."""
    return [OutageRequestPublic.from_record(r) for r in repository.list_requests()]


@app.get("/requests/{request_id}", response_model=OutageRequestPublic)
def get_request(request_id: int) -> OutageRequestPublic:
    """Get one request by id, secrets masked. 404 if it does not exist."""
    record = repository.get_request(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return OutageRequestPublic.from_record(record)


@app.post("/requests/{request_id}/call", response_model=Call, status_code=201)
def start_call(request_id: int) -> Call:
    """Start a call for a request. Refuses if a call is already in progress."""
    record = repository.get_request(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")

    # Double-call guard: do not start a second call while one is running.
    if repository.get_active_call_for_request(request_id) is not None:
        raise HTTPException(
            status_code=409, detail="A call is already in progress for this request"
        )

    payload = build_call_payload(record)
    try:
        started = get_voice_provider().start_call(payload)
    except Exception as exc:  # provider/network error → clean message, not a 500
        raise HTTPException(status_code=502, detail=f"Could not start the call: {exc}")
    call = repository.create_call(request_id, started.provider_call_id, started.status)
    repository.set_request_status(request_id, "calling")
    return call


@app.post("/requests/{request_id}/refresh", response_model=OutageRequestPublic)
def refresh_call_status(request_id: int) -> OutageRequestPublic:
    """Check the provider for the call's latest state. If it ended, mark the
    request 'ended' (ready for a report). Lets the UI update without a webhook."""
    record = repository.get_request(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")

    # Nothing to refresh once a report exists or there is no call yet.
    if record.status == "completed":
        return OutageRequestPublic.from_record(record)
    call = repository.get_latest_call_for_request(request_id)
    if call is None:
        return OutageRequestPublic.from_record(record)

    snapshot = get_voice_provider().fetch_call(call.provider_call_id)
    if snapshot.status in repository.TERMINAL_CALL_STATUSES:
        repository.record_call_result(
            call.id, snapshot.status, snapshot.transcript,
            snapshot.duration_seconds, snapshot.recording_url,
        )
        if record.status == "calling":
            repository.set_request_status(request_id, "ended")
    else:
        repository.advance_call_status(call.id, snapshot.status)

    return OutageRequestPublic.from_record(repository.get_request(request_id))


@app.post("/requests/{request_id}/report", response_model=Report, status_code=201)
def generate_report(
    request_id: int, extractor: Extractor = Depends(get_extractor)
) -> Report:
    """Pull the call transcript, extract a structured report, mark request completed."""
    record = repository.get_request(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")

    call = repository.get_latest_call_for_request(request_id)
    if call is None:
        raise HTTPException(status_code=400, detail="No call to report on for this request")

    # Pull the latest call state (transcript, status) from the provider.
    snapshot = get_voice_provider().fetch_call(call.provider_call_id)
    repository.record_call_result(
        call.id, snapshot.status, snapshot.transcript,
        snapshot.duration_seconds, snapshot.recording_url,
    )

    data = extractor.extract(snapshot.transcript or "")
    report = repository.create_report(call.id, data)
    repository.set_request_status(request_id, "completed")
    return report


@app.post("/webhooks/vapi")
async def vapi_webhook(request: Request) -> dict:
    """Receive call status updates from the provider. Verifies, logs, dedupes, 200 fast."""
    raw = await request.body()
    provider = get_voice_provider()
    if not provider.verify_webhook(dict(request.headers), raw):
        raise HTTPException(status_code=401, detail="Invalid signature")

    body = json.loads(raw) if raw else {}
    event = provider.parse_webhook(dict(request.headers), body)

    call = (
        repository.get_call_by_provider_id(event.provider_call_id)
        if event.provider_call_id
        else None
    )
    if call is None:
        return {"status": "ignored", "reason": "unknown call"}  # fast 200

    inserted = repository.create_status_event(
        call.id, event.status, "webhook", event.provider_event_id, event.occurred_at
    )
    if inserted:
        repository.advance_call_status(call.id, event.status)
        transcript = event.raw.get("transcript")
        if event.status in repository.TERMINAL_CALL_STATUSES and transcript:
            repository.record_call_result(
                call.id, event.status, transcript, event.raw.get("duration_seconds")
            )

    return {"status": "ok", "new": inserted}


@app.get("/requests/{request_id}/report", response_model=Report)
def get_report(request_id: int) -> Report:
    """Return the latest report for a request, or 404 if none yet."""
    call = repository.get_latest_call_for_request(request_id)
    report = repository.get_report_for_call(call.id) if call else None
    if report is None:
        raise HTTPException(status_code=404, detail="No report yet")
    return report


@app.get("/requests/{request_id}/call", response_model=Call)
def get_call_for_request(request_id: int) -> Call:
    """Return the latest call for a request (incl. recording URL + transcript)."""
    call = repository.get_latest_call_for_request(request_id)
    if call is None:
        raise HTTPException(status_code=404, detail="No call yet")
    return call
