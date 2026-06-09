# Outbound AI Voice Agent for ISP Outages — POC Project Plan

> Single source-of-truth planning document for the POC. No application code yet.
> Status: **DRAFT — decisions confirmed + validated against 3 real Cox calls. Ready for Phase 0 on approval.**

---

## 0. Key decisions & assumptions (CONFIRMED)

| # | Decision | Outcome | Why |
|---|----------|---------|-----|
| D1 | Call target during POC | ✅ **Two stages.** **Stage A:** a line the user controls (user role-plays the ISP); ~20–30 test calls. **Stage B:** real ISP IVR/human — only after Stage A is reliable. | Free, repeatable, no legal/recording risk while building. |
| D2 | Voice platform | ✅ **Vapi** *(benchmark-verified)*, isolated behind a `VoiceProvider` interface. **Bland AI = deferred fallback** (§12.5). | Vapi wins on DTMF tool, JSON-schema extraction, BYO-LLM with no markup, 10 free concurrent slots. |
| D3 | Sensitive data (account #, PIN) | ✅ **POC: store normally in local SQLite, mask in the UI.** Fancy protection (DTMF entry, redaction, encryption) → deferred (§12.5). | Local POC; keep it simple. |
| D4 | Call trigger | ✅ Explicit **"Call now"** button. | Easy to demo/re-run; avoids duplicate calls. |
| D5 | LLM | ✅ **Both providers (mix).** **In-call = GPT-4o-mini** (fast, cheap). **Extraction = Claude Sonnet** (most accurate, no-fabrication). Needs an OpenAI key **and** an Anthropic key; BYO via Vapi. | Best of each: latency on the call, accuracy on the report. Cost difference vs. single-provider is cents (telephony minutes dominate). |
| D6 | Headline deliverable | ✅ **A clear summary of the conversation.** ETA included **only if given**; reference/ticket number captured **if given** (often absent — see Cox findings). | ISPs frequently don't provide an ETA; the report is the value, not the ETA alone. |
| D7 | Customer | ✅ **MSP** (manages IT for many businesses). | Trigger is a Utiliko/PSA ticket; MSPs make these calls across many client sites. |
| D8 | Scope | ✅ **ISP outage = beachhead.** Keep the design general so it can extend to other vendor-status calls later. | Same engine (call a vendor, navigate, extract a structured report) generalizes. |
| D9 | Retry (POC) | ✅ **Single attempt:** hold up to a cap (~10–12 min); if no one is reached, report cleanly. User re-clicks "Call now" to retry. Smart auto-retry → deferred (§12.5). | Keep the POC simple. |

---

## 1. Project idea

An **outbound AI voice agent** that calls an ISP when a business has an internet outage, navigates the phone system, and returns a **clear, structured report** — without a person sitting on hold.

In production this is triggered by a **Utiliko** ticket. **For the POC, Utiliko is NOT integrated** — a simple UI lets the user enter the info a ticket would contain.

On each call the agent reaches **one of three responders** and pursues the same goal from whichever it gets:
- 📼 a **recorded IVR/automated message** (e.g., an outage announcement),
- 🤖 the ISP's **AI / virtual agent**, or
- 🧑 a **live human** rep.

The agent tries to learn:
- **Is there an outage?** (and the reason, if stated)
- **Restoration ETA** — *if available* (often it isn't)
- **Who/what** it spoke to (recording / bot / rep name)
- **Timestamp** of the call
- **A faithful summary** for the notes — never fabricating details

> ⚠️ **ISP behavior varies.** Validated with Cox: during a *real* outage Cox routes the caller to an **automated message** with the reason + ETA — *no human*. AT&T/Spectrum/others may differ and use humans. The agent must handle all three responder types.

---

## 2. Problem, users & competitors

### Problem
MSPs (and IT teams) must call ISPs about outages across many client sites — sitting on hold, navigating menus, then manually writing up what they learned. Slow, costly in human time, inconsistent.

### Target user / buyer
- **MSP / IT-operations** company managing IT for many businesses (D7). Buyer = MSP owner/ops lead.

### Value proposition
The differentiator is **not** the AI call itself (commoditized) — it's the **structured, ticketable report fed into the ops workflow**, produced **unattended across many sites**.

### Competitor landscape (honest)
- **Real threat — MSP/PSA/RMM incumbents:** ConnectWise, Datto/Autotask, NinjaOne, Atera. They own the ticket + the customer and could bolt this on as a feature → **moat must be vertical** (per-ISP IVR know-how + deep Utiliko/PSA integration + workflow fit).
- **Voice platforms moving up-stack:** Vapi/Bland themselves (hedged via the `VoiceProvider` interface).
- **"Call on my behalf" analogs:** Google Duplex (feasibility proof), GetHuman/FastCustomer/DoNotPay (wait-on-hold; they just get you a human — they don't produce a structured report).

### Beachhead → expansion (D8)
ISP outage is the **first** call-type. The same engine extends to general **structured vendor-status calls** (carriers, hardware RMA, SaaS support). Keep the report schema generic enough that "outage" is one type among several.

---

## 3. POC scope

### In scope
- UI to enter outage/call info (stand-in for a Utiliko ticket).
- Persist the request.
- Trigger an outbound Vapi call.
- Agent navigates the IVR and handles **recorded message / ISP AI / human**.
- Capture transcript / call result via webhook (+ poll safety-net).
- Extract a structured report (outage? reason, ETA if any, responder, summary).
- Show call status + the report in the UI.

### Functional requirements
1. User submits an outage request (fields in §5).
2. Backend validates and persists with status `new`.
3. User clicks **"Call now"**; backend triggers the call; status → `calling`.
4. Agent navigates IVR, verifies the account, and **captures info from whichever responder it reaches** (recording / bot / human).
5. Vapi posts events to the backend webhook; backend also **polls** for the final result.
6. Backend stores transcript + recording URL + metadata.
7. Backend extracts the structured report **(off the webhook path — see §6)**.
8. UI shows status and the final report.
9. All requests/reports are listable and viewable.

### Non-functional requirements
- **Reliability:** every terminal state (no-answer, voicemail, dropped, gave-up, no-rep-reached, no-outage) yields a **clean status** — never a crash.
- **Accuracy (P0):** the agent/extractor must **never fabricate** an ETA, reason, or reference number. Unknown → `"not provided"`. A confidently-wrong report is worse than none.
- **Observability:** full transcript, recording URL, status history, metadata stored.
- **Idempotency:** one request cannot trigger duplicate concurrent calls; duplicate webhooks are absorbed.
- **Security/PII:** account # and PIN masked in the UI, excluded from logs (D3).
- **Cost-awareness:** holding burns per-minute money → enforce the hold cap (D9).
- **Latency:** in-call turn-taking handled by Vapi; measure it during Stage A.

---

## 4. User flow

1. User opens the web app.
2. User fills the form (phone, account #, PIN, business name, address, ISP, symptoms; optional troubleshooting info).
3. Submit → request saved, status `new`.
4. User clicks **"Call now"** → status `calling`.
5. Agent runs: IVR navigation → verification → reaches recording / bot / human → gathers info.
6. Webhook + poll deliver transcript + result.
7. Backend extracts the report (background) → status `completed` or a terminal failure state.
8. UI shows status + structured summary; user can open the transcript.

---

## 5. Required UI fields

**Form (per request):**
- ISP phone number *(required)*
- Account number *(required, masked after save)*
- PIN *(optional, masked after save)*
- Business name *(required)*
- Business address *(required — also used by IVR verification)*
- ISP / provider name *(optional, helps the agent)*
- Symptoms / notes *(optional)*
- Callback number for the business *(optional)*
- **Troubleshooting already done** *(optional)* — e.g., "modem power-cycled, cables checked"
- **Modem light status** *(optional)* — e.g., "solid white / red / no light"
- **Use "equipment already checked" opening?** *(optional toggle, default OFF)* — lets the agent skip the rep's troubleshooting loop and go straight to the outage question
- **Caller Identity Name** *(optional)* — the name the agent gives on the call ("this is ___ with ___"). *(Added from the "Vivant Downtime Check" design.)*
- **Location Phone Number** *(optional)* — the phone number on the ISP account; IVRs (Cox/AT&T) match the account by this number. *(Added from the "Vivant Downtime Check" design.)*

> **UI wording (adopted from the "Vivant Downtime Check" design):** Location Name (business name) · Location Address · Service/System to Check (ISP/service) · Provider Phone Number (Number to Call) · Account Number · Security PIN · Caller Identity Name · Location Phone Number · Callback Phone. Title: "Vivant Downtime Check — Automated Outage Verification Agent". Call action button: "Dispatch Agent".

**Results view:**
- Status badge (see §14 enum)
- **Outcome** (outage confirmed / no outage / no rep reached / needs review)
- Outage reason
- ETA *(best-effort; "not provided" when absent)*
- Reference/ticket number *(if given — often absent)*
- Who/what it spoke to (recording / bot / rep name)
- Timestamp + duration
- Summary note
- Transcript + recording (expandable)

---

## 6. Backend responsibilities (FastAPI)

- REST endpoints (create / list / get / trigger call).
- Validate + persist to SQLite.
- Build the Vapi call payload (destination + dynamic variables: account/PIN/business/address/ISP/symptoms + per-ISP navigation hints).
- Start the Vapi outbound call **via the `VoiceProvider` interface**; record the provider call ID.
- **Webhook endpoint** that does only: **verify signature → persist raw event + transcript → return 200 fast.**
- **Run extraction OFF the webhook path** (a FastAPI BackgroundTask), so a slow strong-model call never causes a Vapi webhook timeout/retry; re-extraction for `needs_review` is trivial.
- **Poll the provider REST API** a few seconds after call-end as the **primary** source of the final result (webhook = optimization).
- Drive `calls.status` from a `call_status_events` log (enables out-of-order/idempotent handling).
- Mask sensitive fields in responses; keep secrets out of logs.

### Endpoints (draft)
- `POST /api/requests` · `GET /api/requests` · `GET /api/requests/{id}`
- `POST /api/requests/{id}/call`
- `POST /api/webhooks/vapi` *(signature-verified)*

---

## 7. AI agent responsibilities

- **Adapt tone to the responder** *(refined after the first live test):*
  - **To a machine** (IVR / recording / AI bot): keep answers **short**, key word first ("Internet outage." / "Business account." / "Representative."). Long, polite sentences make the IVR mis-hear and say "Sorry." *(AT&T baseline lesson.)*
  - **To a human**: speak **naturally, warmly, politely** in full sentences. Sounding robotic with a person is off-putting and can make them less helpful.
  - When unsure, start natural; switch to short phrases only if it sounds automated or keeps misunderstanding.
- **No filler with machines** ("absolutely," "I appreciate that"); **normal courtesy with humans.**
- Identify itself and state purpose: checking on an outage for a given account/business.
- Navigate the IVR via **DTMF and/or speech** to reach support/outage.
- **Verify the account** (phone number, 4-digit PIN, address, security questions if asked). *(Cox-validated: PIN works; no texted code required.)*
- **Decline deflections:** the "we texted you a link" offer and the "schedule a callback" offer → keep holding.
- **Detect the repeating hold-loop** ("all reps still assisting…") → stay **silent**, do not talk to the recording.
- **Capture from whichever responder it reaches:**
  - 📼 **Recorded outage message** → extract reason + ETA + "technicians dispatched."
  - 🤖 **ISP AI/bot** → ask the outage questions; extract answers.
  - 🧑 **Human** → ask: known outage? ETA? reference number? who am I speaking with?
- *(Optional, default off)* open with "our team already checked the equipment" to skip the troubleshooting loop.
- Know when to give up (hold cap, max duration) and end cleanly.
- **Never fabricate.** If no ETA/reason/reference → report "not provided."

---

## 7.5. Per-ISP IVR playbook (starts with Cox — validated by 3 real calls)

> First entry of a reusable, per-carrier navigation map (a key vertical moat). Build one per ISP over time.

**Cox (validated 2026-05):**
- Account match: enter **10-digit phone number** (DTMF). *May fail to match → expect a retry.*
- Verification: confirm **street number**, then **4-digit PIN** ("press # if unknown"). IVR verify may fail but you can still reach an agent and verify by PIN.
- Menu: **tech support → internet**. (Wrong choice lands in the wrong/slower queue.)
- Deflections: "secure link sent to your device" → **press 0/continue holding**; "schedule a callback" → **decline, keep holding**.
- **Outage case:** caller is routed to an **automated message** stating the outage + ETA (if technicians provided one); **you do NOT reach a human.** **No phone reference number** for outages; updates come via text/app.
- **No-outage case:** reach a **human**, who confirms no area outage (and may try to troubleshoot).

**AT&T (baseline call reviewed 2026-05 — made by a non-engineer, used to set our bar):**
- The IVR is a **talking bot** that asks an open question ("How may I help you?"), not a number menu. Answer with **one short phrase** ("Internet outage.").
- It **loops** on self-service: "check online / can I send you a text?" — repeated twice. **Say no to the text and ask for a representative.**
- Phrase that worked to reach a person: **"speak to a technical support representative"** → "Let me find someone to help you."
- It asks **personal or business account** early → answer **"business."**
- The IVR gave **no outage status and no ETA** on its own; it pushes you to a human or a callback.
- When reps are busy it offers a **callback in 4–6 min** (keypad: press 1 = callback, press 3 = hold). **POC plan: press 3 and hold, or just report the callback offer.** (Actually accepting the callback needs inbound-call handling → deferred, §12.5.)
- **Lesson:** the baseline call talked too much and looped. Our agent must answer short, notice repeats, and ask for a human early.

---

## 8. Vapi call flow

1. Backend (via `VoiceProvider`) starts the call with destination + dynamic variables + system prompt + per-ISP hints.
2. Vapi dials; the assistant runs.
3. Flow: greeting → IVR navigation → verification (phone + PIN + address) → **branch on responder**:
   - automated outage message → capture reason + ETA;
   - ISP AI/human → ask the outage questions.
4. Vapi streams status events to the webhook (`ringing`, `in-progress`, `ended`, …).
5. On end, Vapi sends the end-of-call report (transcript, recording, duration, structured output if configured).
6. Backend persists, **and polls the REST API** for the final structured output (primary), webhook as backup. Extraction runs as a BackgroundTask.

---

## 9. Data that should be saved

- The original request (all fields; account/PIN stored normally per D3, masked in UI).
- Provider call ID + metadata.
- **Status history** (each transition with timestamp + source).
- Full transcript.
- Recording URL (if available).
- Duration + start/end timestamps.
- Extracted report (outcome, reason, ETA, reference #, responder, summary).
- Raw webhook payloads (debug).

---

## 10. Final report format

```json
{
  "request_id": 123,
  "business_name": "Acme Corp",
  "isp_name": "Cox",
  "call": {
    "provider_call_id": "...",
    "started_at": "2026-05-29T15:00:00Z",
    "ended_at": "2026-05-29T15:07:42Z",
    "duration_seconds": 462,
    "status": "completed",
    "recording_url": "https://..."
  },
  "report": {
    "outcome": "outage_confirmed_with_eta",
    "responder": "recorded_message",
    "outage_reason": "Area outage; technicians dispatched.",
    "estimated_restoration": "Today by ~6:00 PM (per automated message)",
    "reference_ticket": "not provided",
    "spoke_with": "Automated outage announcement",
    "timestamp": "2026-05-29T15:02:10Z",
    "summary": "Cox automated message confirmed an area outage, technicians dispatched, ETA ~6 PM. No phone reference number; updates via Cox app/text."
  },
  "transcript_available": true
}
```

**Realistic "no outage" example** (the Cox call #3 case):
```json
{
  "report": {
    "outcome": "no_outage_found",
    "responder": "human",
    "outage_reason": "not provided",
    "estimated_restoration": "not provided",
    "reference_ticket": "not provided",
    "spoke_with": "Rep 'Jasmine'",
    "summary": "Rep checked account + area: no outage on record; line up consistently. Likely local/equipment issue — recommend on-site check."
  }
}
```

`outcome` enum: `outage_confirmed_with_eta` · `outage_confirmed_no_eta` · `no_outage_found` · `equipment_issue` · `no_rep_reached` · `needs_review`.

---

## 11. Edge cases

- No answer / busy / invalid number / SIT tones.
- Voicemail / answering machine → don't converse with it; mark `voicemail`.
- **Endless hold, no one answers** *(seen live)* → hold to the cap, then **give up** and report `no_rep_reached`. *(POC: single attempt; user re-triggers.)*
- **Hold-loop recording** repeating → agent stays **silent**, keeps holding.
- **DTMF / account match fails** *(seen live)* → retry; if still failing, report cleanly.
- **IVR PIN verify fails** but agent path still reachable → continue to a human and verify there.
- **SMS-link / callback deflection** → decline, keep holding.
- **Outage → automated message, no human** *(Cox)* → capture the recording's reason + ETA.
- **No ETA available** (techs haven't provided one) → "not provided."
- **No reference number** (Cox) → "not provided."
- Rep wants to troubleshoot equipment → capture outcome; recommend on-site (agent can't see lights).
- Call dropped → save partial transcript, mark `partial`.
- Webhook late / out-of-order / duplicate → idempotent (status-event log).
- Duplicate "Call now" → DB-level guard blocks a second in-flight call.
- Extraction missing/uncertain → store transcript, mark `needs_review`.

---

## 12. Out-of-scope items (POC)

- Utiliko integration (ticket ingest / write-back).
- Multi-tenant, auth/roles, billing.
- Production-grade security/compliance.
- Scaling, real queues, retries-at-scale, concurrency.
- Calling many ISPs in parallel / scheduling / batching.
- Multi-language; voicemail message composition.
- Polished/branded UI.

---

## 12.5. Production Hardening (DEFERRED — good ideas, NOT for the POC)

> Captured so nothing is lost; deliberately out of focus now.

**Security / sensitive data**
- Enter the PIN as **DTMF tones** (keep it off the spoken transcript).
- **Redact** credential patterns from transcripts before storage.
- **Encrypt** stored secrets at rest.

**Voice platform**
- **Bland AI** as a drop-in for the `VoiceProvider` slot (purpose-built for outbound + IVR/hold). Swap in if Vapi DTMF/IVR is unreliable on real ISPs.
- **Per-ISP provider routing (decide AFTER testing Vapi):** the `VoiceProvider` interface already lets us pick a *different* voice platform per ISP / target type — e.g. `{ AT&T → Bland, Cox → Bland, Spectrum → Vapi, human → Vapi, default → Vapi }`. Use the best tool for each ISP's IVR.
  - **Don't build the routing yet — test Vapi first.** Vapi *can* navigate IVRs (DTMF + menus); Bland is more purpose-built for outbound/IVR/hold but may not be needed. Only add per-ISP routing once a live test shows Vapi failing on a specific ISP. (Avoids the cost of multiple accounts/keys/assistants before it's justified.)
  - **Cheap setup option:** add an `ISP → provider` config map (all defaulting to Vapi) so switching one ISP to Bland later is a one-line change — zero added complexity today.
  - **Pairs with per-ISP playbooks (§7.5):** each ISP could eventually get its own *provider* AND its own tuned *assistant/prompt*. Strong, defensible design (per-ISP IVR know-how = the vertical moat).
  - **What Vapi/Bland actually are:** voice-orchestration platforms that wrap telephony + speech-to-text + the LLM brain (GPT in-call) + text-to-speech + real-time turn-taking. They are the "ears, mouth, phone line, and conductor"; the LLM is the brain. DIY (Twilio + Deepgram + LLM + ElevenLabs + own media server) is possible but weeks of real-time engineering — not worth it for the POC.

**Retry / persistence (smart version)**
- **Auto-retry after a delay** (not instant — instant redial rejoins the back of the same queue). Max 2–3 attempts, **total time/cost cap**, off-peak timing.
- **Accept the ISP callback** when offered (needs inbound-call handling).
  - **Two-agent design (idea):** one **outbound agent** makes the first call, and a separate **inbound agent** answers when the ISP calls back. Splitting the job keeps each agent's prompt smaller and cheaper, and it makes the callback path actually work (the AI can pick up the return call). *(From the AT&T baseline: AT&T offered a callback in 4–6 min — an outbound-only agent can't use that.)*

**Compliance (mandatory before real-ISP / production use)**
- AI-identity disclosure in the opening line (e.g., CA SB 1001-style).
- Recording-consent handling for two-party-consent states.
- Caller-authorization ("authorized representative") posture.

**Alternative data source**
- Where the ISP exposes it (e.g., Cox app/outage map/text updates), **pull outage status via app/API** instead of (or alongside) calling.

**Scale / infrastructure**
- SQLite → Postgres · UI polling → SSE/WebSocket push · BackgroundTask extraction → job queue.

**Bulk / multi-site**
- **Bulk Audit — "Process Outage CSV":** upload a network-inventory CSV and run outage checks across many sites in one sweep (from the "Vivant Downtime Check" design). POC stays single-site; this is the multi-site expansion.

**Agent evaluation — "LLM-as-a-judge" (quality QA)**
- A **second AI agent (the "evaluator / judge")** reads each call transcript and **scores how well the outage agent performed** — turning every call into measurable quality data for continuous improvement and regression testing (catch when a prompt change makes things worse).
- **Metrics (current standard "agent-eval" dimensions):**
  - **Goal completion / task-success rate** — did it get outage status + ETA + ticket when those were available?
  - **Faithfulness / no-hallucination** — cross-check the report against the transcript; did it avoid inventing an ETA/reason/ticket?
  - **Rule adherence** — terse with machines, natural with humans, declined the "text me a link" offer, asked for a rep when looping, ended the call cleanly.
  - **Efficiency / conversation quality** — turns taken, latency, dead-air, over-talking.
  - **Responder handling** — did it correctly adapt to IVR vs bot vs human?
- **Method:** LLM-as-a-judge with a **rubric** (e.g. 1–5 per dimension) + pass/fail flags; aggregate across calls into a quality dashboard; use it to **A/B-test prompts** and **compare providers** (Vapi vs Bland). A separate Claude call (own backend) gives full control of the rubric.
- **Note:** Vapi also has a built-in **"Evals"** feature (dashboard sidebar) that could complement or seed this.

---

## 13. Recommended architecture

```
┌────────────┐      REST       ┌──────────────┐   VoiceProvider    ┌──────────┐
│  React UI  │ ───────────────▶│   FastAPI    │ ─── (Vapi impl) ──▶ │   Vapi   │
│ (form +    │ ◀─────────────── │  backend     │                    │ (call +  │
│  results)  │   JSON / poll    │              │ ◀── webhook ─────── │  agent)  │
└────────────┘                  │   SQLite     │ ──► poll (primary)  └────┬─────┘
                                └──────┬───────┘                          │ phone
                         BackgroundTask│ extraction (Claude Sonnet)       ▼
                                       ▼                          ISP (recording /
                                 structured report                 bot / human)
```

- **Frontend:** React (form, list, results card, transcript). Polls `GET /api/requests/{id}`.
- **Backend:** FastAPI (REST + signed webhook + poller), SQLite via a thin data layer.
- **Voice:** Vapi behind the `VoiceProvider` interface.
- **Extraction:** Vapi structured analysis preferred; fallback = one **Claude Sonnet** call over the transcript, run as a BackgroundTask.
- **LLM (D5):** **GPT-4o-mini in-call** (fast) + **Claude Sonnet for extraction** (accurate).
- **Secrets:** `.env` (Vapi key, **OpenAI key**, **Anthropic key**, **Vapi webhook signing secret**, public webhook URL via ngrok in dev).

---

## 14. Suggested database tables

**`outage_requests`**
| column | type | notes |
|--------|------|-------|
| id | INTEGER PK | |
| isp_phone | TEXT | |
| account_number | TEXT | stored; masked in UI |
| pin | TEXT | stored; masked in UI; never logged |
| business_name | TEXT | |
| business_address | TEXT | |
| isp_name | TEXT | nullable |
| symptoms | TEXT | nullable |
| troubleshooting_done | TEXT | nullable |
| modem_light_status | TEXT | nullable |
| use_equipment_checked_opening | BOOLEAN | default false |
| callback_number | TEXT | nullable |
| status | TEXT | see status enum |
| created_at / updated_at | DATETIME | |

**`calls`**
| column | type | notes |
|--------|------|-------|
| id | INTEGER PK | |
| request_id | INTEGER FK | → outage_requests.id |
| provider_call_id | TEXT | **UNIQUE** |
| status | TEXT | denormalized latest (driven by events) |
| started_at / ended_at | DATETIME | nullable |
| duration_seconds | INTEGER | nullable |
| recording_url | TEXT | nullable |
| transcript | TEXT | nullable |
| created_at | DATETIME | |

**`call_status_events`** *(new — enables out-of-order/idempotent handling + history)*
| column | type | notes |
|--------|------|-------|
| id | INTEGER PK | |
| call_id | INTEGER FK | → calls.id |
| status | TEXT | |
| source | TEXT | webhook / poll / api |
| provider_event_id | TEXT | **UNIQUE** (dedupe) |
| occurred_at / received_at | DATETIME | |

**`reports`**
| column | type | notes |
|--------|------|-------|
| id | INTEGER PK | |
| call_id | INTEGER FK | → calls.id |
| outcome | TEXT | outcome enum |
| responder | TEXT | recorded_message / bot / human |
| outage_reason | TEXT | nullable |
| estimated_restoration | TEXT | verbatim; nullable |
| eta_normalized | DATETIME | nullable |
| eta_is_estimate | BOOLEAN | |
| reference_ticket | TEXT | nullable |
| spoke_with | TEXT | nullable |
| call_timestamp | DATETIME | nullable |
| summary | TEXT | nullable |
| review_state | TEXT | ok / needs_review |
| created_at | DATETIME | |

**`webhook_events`** (raw debug/audit)
| column | type | notes |
|--------|------|-------|
| id | INTEGER PK | |
| call_id | INTEGER FK nullable | |
| event_type | TEXT | |
| payload | TEXT (JSON) | raw |
| received_at | DATETIME | |

**Status enum:** `new` · `calling` · `completed` · `failed` · `no_answer` · `voicemail` · `partial` · `no_rep_reached` · `no_outage_found`.

---

## 15. Implementation phases (TDD — test first, approval each step)

- **Phase 0 — Skeleton:** repo structure, FastAPI boots, SQLite connects, React boots, `.env`. *(tests: health, DB)* ✅ **DONE**
- **Phase 1 — Request CRUD:** models + create/list/get + UI masking. *(tests: create, validate, mask, list, get)* ✅ **DONE (backend; 14 tests passing)**
- **Phase 2 — UI form + list:** form submit + list + minimal results view. *(tests: render + API mock)* ✅ **DONE (React form + list, verified live; frontend auto-tests deferred)**
- **Phase 3 — Call trigger + `VoiceProvider`:** `POST /requests/{id}/call`, payload builder, **full interface contract** (`start_call`, `parse_webhook → normalized event`, `fetch_call`, structured-output accessor), DB-level duplicate-call guard. *(tests: payload, contract w/ Vapi + stub, idempotency, status transition)* ✅ **DONE (interface + Stub provider + trigger + guard; real Vapi impl deferred to live-call phase)**
- **Phase 4 — Webhook intake:** **signature verification**, status-event log, dedupe, fast 200. *(tests: unsigned → 401, parse, dedupe, out-of-order)* ✅ **DONE (HMAC verify + call_status_events log + dedupe + forward-only status; tested with stub)**
- **Phase 5 — Extraction (BackgroundTask):** transcript → report; never-fabricate rule; `needs_review` fallback. *(tests: fixtures — outage-with-ETA, outage-no-ETA, no-outage, hold-loop, vague/conflicting → "not provided")* ✅ **DONE (Claude extractor + never-fabricate logic + reports table + report endpoint; verified live on the AT&T transcript)**
- **Phase 6 — Results UI + polling:** status badge, outcome, report card, transcript. *(tests: render, polling)* ✅ **DONE (report card UI + Get Report action + GET report endpoint; live polling deferred)**
- **Phase 7 — Stage A live calls:** ~20–30 calls to the user-controlled line; tune agent + per-ISP playbook; **measure latency + accuracy**. *(manual checklist + go/no-go bar)*
  - ✅ **Vapi connected + first live call succeeded.** Real `VapiVoiceProvider` auto-used when `VAPI_API_KEY` set. Human-rep path tested end-to-end (real call → real conversation → Claude report). Agent tone made **adaptive** (natural with humans, terse with machines) after this test.
  - ✅ **IVR navigation (DTMF) — PASSED.** Built a Twilio test IVR (AT&T-style, 2-level menu) and Vapi's `dial_keypad`/DTMF tool. The agent called in, **navigated the menu itself (pressed 2 → 2)**, reached the outage message, and Claude extracted a perfect report (outage confirmed, fiber cut, 6 PM ETA, ticket 12345) with recording + transcript. **Vapi handles IVR/DTMF** for a clean 2-level menu → no need for Bland here (per-ISP/Bland stays parked in §12.5). See [test-ivr-twiml.md](test-ivr-twiml.md).
  - ✅ **HARD IVR stress test — PASSED.** Built a deeper branching IVR (Twilio Function, [hard-ivr-function.js](hard-ivr-function.js)): 4 levels, 5-option main menu, decoy/wrong-turn recovery, retry-on-no-input, and **keypad data entry** ("enter your 10-digit number + #"). The agent navigated **main→tech support (3)→internet (2)→report outage (2)→entered the number+#** and got the result; Claude reported it perfectly (severe weather, 9 PM, ref 67890). **Picks the right option among many, enters data on the keypad, doesn't get stuck.**
  - ✅ **Conversational ISP bot test — PASSED.** Built a 2nd Vapi assistant ("Fake AT&T Bot") that role-plays a talking ISP (greets, asks personal/business, **self-service loop** "can I text you?", then hands off to an interactive "tech support rep"). The agent **declined the text offer twice, asked for a representative, did interactive Q&A with the rep, got the info, and confirmed it.** Report perfect (responder=human, fiber cut, 7 PM, ticket 99887). This covers the conversational ISP case (real AT&T behaves this way), not just keypad menus.
  - 🐞 **Bugs found + fixed during conversational test:** (1) Vapi inbound number didn't actually have the bot attached (assignment didn't persist while "Activating") → fixed via API. (2) **"Goodbye loop"** — two polite AIs said goodbye forever because the agent's hangup never fired: the trigger phrases had been pasted into **End Call Message** instead of **End Call Phrases**, and `maxDurationSeconds` hadn't saved. Fixed: real `endCallPhrases`, `endCallMessage="Goodbye."`, `maxDurationSeconds=600`.
  - ✅ **HARD conversational stress test — PASSED.** Built a separate "Hard AT&T Bot" (own assistant, swap onto the bot number) with: obtuse opener, **double self-service deflection**, a **verification gauntlet** (account # → PIN → address), a **hold/callback** offer, then an interactive rep. The agent cleared **every** hurdle — clarified "internet", said "business", declined the text twice, **provided account number / PIN / address from its variables when legitimately asked**, chose to hold, escalated, and extracted the facts (damaged fiber line, 8 PM, ticket 55432) — then hung up cleanly. Report perfect.
  - 🧰 **Reusable test-bot library + Twilio outbound:** test scenarios = separate Vapi assistants (Normal AT&T, Hard AT&T), swapped onto one bot number (dashboard dropdown or `PATCH /phone-number {assistantId}`). **Vapi-bought numbers have a daily outbound limit;** fixed by **importing a Twilio number into Vapi for outbound** (`+13074051286`, no cap) → set as `VAPI_PHONE_NUMBER_ID`. Also hardened the app to return a clean error (502 + message) instead of a 500 when a call can't start.
  - 🔁 **Agent now speaks SECOND (waits for the ISP), not first.** In real telephony the answerer (ISP) speaks first and the caller responds — so the agent waits, hears the greeting/menu, and reacts. Set `firstMessageMode=assistant-waits-for-user` on the agent; test bots set to greet first (`assistant-speaks-first`). This **fixed the start-collision** cleanly and **verified working on the IVR** (navigates fine) and natural for humans. (The mid-call **AI-to-AI** turn-taking flakiness is separate and still the hard case.) Safeguard to add later: have the agent open the call itself if the ISP is silent for a few seconds.
  - ⭐ **KEY CHALLENGE — AI-to-AI turn-taking (this is a REAL production issue, not a test artifact).** AT&T's real system is itself a conversational **AI** (per the baseline transcript), so calling AT&T = **our AI talking to their AI**, and the same is increasingly true of other ISPs. In AI-to-AI calls the agent sometimes doesn't detect that the other AI finished speaking (endpointing is tuned for human speech rhythms, not synthetic voices) → it stays silent and the call dies on silence-timeout. **Levers applied:** `silenceTimeoutSeconds` 15→30 (both sides), and **LiveKit smart endpointing** (`startSpeakingPlan`) on the agent. **This is an area that needs iteration/tuning, not a one-click fix** — worth evaluating whether Bland or different endpointing settings handle AI-ISP conversations more reliably (ties to per-ISP provider routing, §12.5). Human + IVR paths are reliable; the AI-vs-AI conversational path is the one to keep hardening.
  - ⏭️ Webhook (ngrok) still optional — reports currently work via polling (`fetch_call`); add the live webhook for real-time status updates.
  - ⏭️ Caller-ID "SPAM/Scam Likely" on the Vapi number → branded caller ID / number registration (see §12.5).
- **Phase 8 — Stage B real-ISP calls:** only after Stage A passes + compliance gate (§12.5). Real ISP; capture recording/bot/human paths. *(manual checklist + kill-criteria)*

---

## 16. Testing strategy

- **Unit (TDD, primary):** validation, masking, payload builder, signature verify, status-event dedupe/ordering, idempotency, extraction parsing.
- **Integration:** request → trigger → webhook+poll → report happy path with a stubbed provider.
- **Sample-transcript fixtures:** outage-with-ETA, outage-no-ETA, no-outage (Cox #3), endless-hold/no-rep, voicemail, dropped, vague/conflicting ETA → must output "not provided" (never fabricate).
- **Frontend:** form submit, list, results, polling.
- **Manual E2E — Stage A (Phase 7):** ~20–30 controlled calls; verify capture, extraction, accuracy, latency.
- **Manual E2E — Stage B (Phase 8):** real ISP; recording/bot/human paths.
- **Go/no-go bar (before trusting the product):** define a minimum % of calls producing a correct, non-hallucinated report; treat a fabricated ETA as a P0 failure.

---

## Appendix — Real-call validation (Cox, 2026-05)
- **Call 1:** PIN/security-question verification (no texted code); call became live troubleshooting (modem lights/reboot); "no outage" still produced a useful summary.
- **Call 2:** entered account → endless hold loop → no answer after ~10 min (the `no_rep_reached` edge case; no callback offered).
- **Call 3:** confirmed — during a **real outage Cox plays an automated message with the ETA, no human**; **no phone reference number** (updates via app/text); ETA only if technicians provided one. Verified again with PIN.
