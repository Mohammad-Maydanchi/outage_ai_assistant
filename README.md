# Vivant Downtime Check — Outbound AI Voice Agent for ISP Outages

A proof-of-concept **outbound AI voice agent** that calls an internet service
provider (ISP) when a business has an internet outage, navigates the phone
system (human reps, IVR menus, or automated bots), and returns a **clean,
structured, never-fabricated report** — without a person sitting on hold.

The differentiator isn't the AI call (commoditized) — it's the **structured,
ticketable report** produced unattended.

---

## What it does

1. **Enter an outage** in a web form (stands in for a Utiliko/PSA ticket).
2. **Dispatch the agent** — it calls the ISP and navigates whatever it reaches:
   - 🧑 a live **human** rep,
   - ⌨️ a keypad **IVR menu** (presses digits / enters data via DTMF),
   - 🗣️ a conversational **AI/bot** (handles self-service loops, asks for a rep).
3. **Listen** to call status updates (signed webhook).
4. **Write the report** — Claude reads the transcript and extracts: outage
   confirmed? reason? ETA? reference #? who it spoke to? — and **never invents
   anything** ("not provided" when absent; `needs_review` when unclear).
5. **Read it on screen** — a report card with the outcome, summary, call
   **recording**, and full **transcript**.

## Proven end-to-end (live calls)

| Call type | Status |
|---|---|
| Live human rep | ✅ |
| Simple keypad IVR | ✅ |
| Hard branching IVR (decoy menus + keypad data entry) | ✅ |
| Conversational ISP bot (self-service loop → rep hand-off) | ✅ |

---

## Architecture

- **Frontend:** React (Vite) — the form, the request list, the report card.
- **Backend:** FastAPI (REST + signed webhook), SQLite via a thin data layer.
- **Voice:** Vapi, behind a swappable `VoiceProvider` interface (a `Stub` for
  tests, the real `Vapi` provider when a key is set; Bland AI could drop in).
- **In-call brain:** GPT-4o-mini (fast). **Report extraction:** Claude Sonnet
  (accurate, no fabrication).
- **Tests:** 49 passing (TDD) — validation, masking, repository, endpoints,
  webhook (signature/dedupe/ordering), extraction rules, Vapi provider.

```
backend/
  app/
    main.py          # FastAPI endpoints
    models.py        # data shapes + secret masking
    repository.py    # SQLite data layer
    db.py            # SQLite connection
    config.py        # loads secrets from .env
    extraction.py    # Claude report extraction (never-fabricate)
    security.py      # webhook signature verification
    voice/           # VoiceProvider interface + Stub + Vapi + payload builder
  tests/             # 49 tests
frontend/
  src/App.jsx        # form + list + report card
docs/
  project_plan.md    # full plan, decisions, future works
  test-ivr-twiml.md  # Twilio test IVR scripts
  hard-ivr-function.js  # Twilio Function: hard branching IVR
```

---

## Run it locally

### 1. Secrets — create `backend/../.env` (project root `.env`)
```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
VAPI_API_KEY=                 # optional — without it, a fake phone is used
VAPI_PHONE_NUMBER_ID=
VAPI_ASSISTANT_ID=
VAPI_WEBHOOK_SECRET=
DATABASE_URL=sqlite:///./outage.db
```
> `.env` is git-ignored — your keys never get committed.

### 2. Backend
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev          # opens on http://localhost:5174
```

### 4. Tests
```bash
cd backend && .venv/bin/python -m pytest -q
```

Without a `VAPI_API_KEY`, the app uses a **fake phone** (no real calls, no
cost) — everything works end-to-end for development. Add the Vapi key to place
real calls.

---

## Status

POC core is **complete and tested**. Remaining work (compliance for real-ISP
calls, branded caller ID, per-ISP provider routing, LLM-as-a-judge evaluation,
bulk multi-site, report sharing/export) is captured in
[docs/project_plan.md](docs/project_plan.md) under "Production Hardening".
