# Demo & Presentation Plan — Vivant Downtime Check

> Plan for a **15-minute HTML presentation + demo** of the outbound AI voice agent.
> Status: **✅ BUILT — `docs/demo/demo.html` is complete and renders.** Reviewed by an evaluation agent; fixes applied.
> Open for the user to finalize: (1) record `app-run.mov`, (2) confirm the problem stat on slide 2, (3) confirm the closing ask on slide 11. Both bookends have sensible placeholders marked `EDIT` in the deck.

---

## 🔄 Revision 4 (focus on the work, not the problem)

- The CEO already knows the problem, so: **removed the ROI slide entirely**, and **cut the problem down to one tight slide** ("Outage calls tie up your team… Here is what we built") that pivots straight to the solution.
- **Added two engineering-depth slides** to show the work can actually solve it:
  - *Built the way production software is built* — test driven with 49 tests, clean architecture, two models on purpose, secure by default (signed webhooks, no duplicate calls, masked PII).
  - *We tried to break it before a provider could* — our own keypad menus and bots built to test against, the four level menu with data entry, the verification gauntlet, the agent waiting to speak and hanging up cleanly, the AI to AI turn taking frontier, and clean failure handling.
- The standalone "providers are becoming AI" slide was **folded into the stress test slide** (it is an engineering point now, not a tangent).
- Act structure updated: I Context · II Solution · III See it work · IV How we built it · V What's next. Still **16 main slides + appendix**.

## 🔄 Revision 3 (more appeal + ROI, ROI later removed in rev 4)

- **New ROI slide** right after the problem (slide 3), aimed at a CEO who thinks in return. The headline return is **time**: ~30 min saved per call → 20 hrs/month → 240 hrs/year (about six work weeks), with a note that money follows from the time. Volume numbers are flagged `EDIT` (illustrative until real figures are dropped in).
- **Visual polish:** radial gradient background with a soft vignette, a faint dot grid, slide entrance animation (gentle rise), hover lift on the cards, a glowing progress bar, and big gradient numbers on the ROI slide.
- Deck is now **16 main slides + appendix**.

## 🔄 Revision 2 (user feedback applied)

- **No hyphens or dashes** anywhere in prose (only the literal filenames `app-run.mov` / `app-run.mp4` keep theirs). Simpler words and shorter sentences throughout.
- **Title slide** is now centered and balanced, with three chips ("Calls the provider · Navigates any phone system · Writes the report") that say what it is.
- **Problem slide** rewritten in plain language, centered and distributed.
- **Five scenarios, one slide each** (replacing the single montage): an intro slide ("A call can go five ways. We handle all five.") then one slide per scenario, each with **its audio and full transcript side by side**, the transcript highlighting line by line as the call plays. Order: live person → simple keypad menu → hard branching menu → talking bot → the hardest test (the gauntlet). New recording added for the simple bot: `snippet-bot-simple.wav` (call 23, ticket 99887).
- **Closing slide** reframed: removed the "let us run a pilot" ask. It now states the roadmap and a confident closing line about the product's direction.
- Deck is now **15 main slides + appendix** (was 11).

## ✅ What was built (`docs/demo/`)

- **`demo.html`** — self-contained vanilla-JS deck, 11 slides in 4 acts + 1 appendix slide. Renders offline; verified via headless Chrome (title, report card, montage all correct). JS syntax-checked.
  - Keyboard nav (← → / Space / Home / End), click left/right half to move, **progress bar + slide counter + act label**.
  - **Speaker notes** on every slide — press **S** to toggle. TODO markers highlighted.
  - **Slide 6 (hero call):** embedded `gauntlet-recording.wav` with a **karaoke-style transcript** that auto-highlights and scrolls as the audio plays (approximate sync by line length — no timestamps needed).
  - **Slide 7 (report):** the gauntlet report rendered as **live HTML** (fiber line, 8 PM, ticket 55432).
  - **Slide 9 (montage):** 4 real call clips — **human, simple IVR, hard IVR, conversational bot** — each plays the opening ~15–20s then auto-stops; a "play full call" button removes the cap.
  - **Slide 5 (demo video):** `<video>` wired to `app-run.mov` / `app-run.mp4` with a **styled placeholder + record instructions** shown until the file exists.
  - **Appendix (press A):** the agent's real system prompt, for technical Q&A.
- **Assets copied/downloaded into `docs/demo/`:** `gauntlet-recording.wav`, `audio-poster.png`, and 4 montage snippets pulled from the DB's Vapi recordings — `snippet-human.wav` (call 10), `snippet-ivr-simple.wav` (call 11), `snippet-ivr-hard.wav` (call 14), `snippet-bot.wav` (call 28). **Now self-contained — no dependency on live Vapi URLs.**

**To finish:** record `app-run.mov` into `docs/demo/`, then edit the two `EDIT`-flagged lines (problem stat, the ask).

---

## 0. Goal

Produce a **self-contained, compelling HTML presentation** that, in ~15 minutes,
shows: **the problem → the solution → a working demo → why it's trustworthy → what's next.**
The proof is the demo: a real call you can *hear* and the app you can *see* working.

---

## 1. Decisions (confirmed)

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Format | **Self-contained HTML deck** (`docs/demo/demo.html`) | Plays real audio + screen recording inline; runs offline on any laptop/browser; easy to share afterward. |
| 2 | Tech | **Vanilla JS, zero dependencies** | Most robust for a live talk on any machine; works from `file://`, no internet needed. |
| 3 | In-app demo | **Pre-recorded, muted screen capture**, narrated live | No live-call risk; full control of pacing; always works. |
| 4 | Hero audio | **`gauntlet-recording.wav` (~3.2 min)** — play in full or lightly trimmed | The full call is only ~3.2 min (191.6s), so it fits the 2:30 slot with light trimming; no need for an aggressive 60–90s cut. |
| 5 | Story spine | **One scenario throughout** (Vivant Corp, 2727 Linden, Dallas — the gauntlet call) | Audio + video + report all tell the *same* story → coherent, memorable. |
| 6 | Source of copy | **Reuse text from `docs/make_deck.py`** | Keeps the HTML deck and the existing PPTX consistent. |
| 7 | Audience | **Business buyer (MSP owner / ops lead)** — per `project_plan.md` D7 | Drives the 15-min length and the "hide the plumbing" call (§7). *Note: an expert reviewer assumed a technical audience (20–25 min, show architecture); that framing was considered and set aside for this buyer-focused talk.* |
| 8 | Speaker notes | **Per-slide speaker notes in the HTML** (hidden presenter notes) | Presenter knows exactly what to say; supports rehearsal and consistency. (AI-synthesized narration considered, deferred.) |
| 9 | Call-path coverage | **Hero call + breadth montage.** Play the hardest path (gauntlet) in full on slide 6; play 10–15 sec snippets of the other 4 paths on slide 9. | The audience *hears* all 5 paths (human / simple IVR / hard IVR / bot / gauntlet), not just a checklist — without playing 5 full calls. Recordings already exist in the DB (§3a-bis). |

---

## 2. The 15-minute narrative (slide-by-slide)

Timing in brackets; total ~15–16 min (the slide-9 montage adds ~45s; trim slide 10 and the intros to stay near 15). Slides 5, 6 & 9 are the heart — about half the time is *showing/hearing it work*. The 11 slides group into a clean **4-act spine** (per the expert's recommended structure): **Act I — Problem · Act II — Solution & how it works · Act III — Live demo · Act IV — Conclusion & future work.**

| # | Act | Slide | Content | Media | Time |
|---|-----|-------|---------|-------|------|
| 1 | I | **Title** | "Vivant Downtime Check — an AI that calls your ISP so no one sits on hold." | — | 0:30 |
| 2 | I | **The problem** | MSPs/IT teams call ISPs across many sites → hold, menus, manual notes. Slow, costly, inconsistent. Quantify (e.g. 20–40 min/call × many sites). | — | 1:30 |
| 3 | II | **The insight / solution** | The AI call is commoditized — the **moat is the structured, never-fabricated, ticketable report produced unattended.** | — | 1:30 |
| 4 | II | **What it does (the loop)** | 5 steps: enter outage → dispatch → navigate (human / IVR / bot) → extract → read report. **One line on voice platform:** "Voice runs on Vapi, behind a swappable provider interface — a choice, not a lock-in." (See §7.) | small diagram | 1:30 |
| 5 | III | **★ DEMO — the app** | Screen recording: enter the outage (the stand-in for a ticket) → **Save request** → row appears → **Dispatch Agent** (badge → Calling…) → the agent places the call → call ends → **Get Report** → report card (outcome, ETA, transcript). | **video (muted, narrate live)** | 3:00 |
| 6 | III | **★ Hear it work** | The hard gauntlet call. Set up the stakes (verification gauntlet, double deflection, hold-for-rep). **Transcript/beat-markers shown on-screen, synced to playback** so the listen-only stretch stays visual. | **gauntlet audio + on-screen transcript** | 2:30 |
| 7 | III | **The report it produced** | The extracted report for *that exact call*: damaged fiber line, 8 PM, ticket 55432, responder = human. | report card (live HTML) | 1:00 |
| 8 | III | **The golden rule** | Never fabricate. "not provided" / "needs review." A confidently-wrong report is worse than none. | — | 1:00 |
| 9 | IV | **Proven end-to-end — every call path** | Test matrix: human ✅ · simple keypad IVR ✅ · hard branching IVR ✅ · conversational bot ✅ (+ the hard gauntlet from slide 6). **Play a 10–15 sec snippet of each of the other 4 paths** as a quick "breadth montage" so the audience *hears* the range, not just a checklist. Plus "49 tests passing" + one line: we built our own IVRs/bots (on Twilio) to stress-test before touching a real ISP. | **4 short audio snippets** | 1:30 |
| 10 | IV | **Strategic insight** | ISPs are *becoming AI* → we tested AI-vs-AI, the real hard case (turn-taking). **Keep to ~30s** — it's a tangent right before the ask; don't lose momentum. | — | 0:30–0:45 |
| 11 | IV | **What's next / the ask** | Compliance, branded caller ID, per-ISP routing, LLM-as-judge, bulk multi-site. End with the ask. | — | 0:45 |

---

## 3. Media plan

### 3a. Audio — already have it (`docs/gauntlet-recording.wav`)
- **Hero asset.** Actual length is **~3.2 min (191.6s)** — it fits the 2:30 slot with only light trimming. (Earlier draft wrongly said 7 min; the PPTX correctly says ~3.5 min.)
- **Action:** play it through, or trim lightly (top/tail dead air, maybe shorten the hold section) with `ffmpeg`. The full arc is: double "can I text you the link?" deflection → ask for a rep → give account/PIN/address → hold → get outage facts (reason + ETA + ticket).
  - If a shorter cut is wanted, derive points from `docs/full_transcript.txt`.
- Keep the **full WAV** behind a "play full call" link for Q&A regardless.
- Use `docs/audio-poster.png` as the player poster image.
- **Mitigate the listen-only risk:** render the transcript (already in `make_deck.py`) on the slide and highlight/scroll beats as the audio plays, so the audience tracks the story visually. Test on the actual room speakers beforehand — phone-quality mono over bad room audio is a real risk.

### 3a-bis. Breadth montage — 4 short snippets (slide 9)
- **Goal:** let the audience *hear* all the call paths, not just see a checklist. Covers: **agent→human**, **agent→simple keypad IVR**, **agent→hard branching IVR**, **agent→simple conversational bot**. (The hardest path — agent→agent gauntlet — is already the hero on slide 6.)
- **Source — already available, no re-recording needed:** the SQLite DB (`backend/outage.db`, `calls.recording_url`) holds **30+ past call recordings** on Vapi storage. **Verified reachable** (a full URL returns HTTP 200, a ~10 MB WAV). *Note: these are Vapi-hosted links and could expire — download the chosen clips to `docs/demo/` soon so the deck is self-contained and not dependent on a live URL.*
- **Build task:** read the transcripts in the DB, pick one clean call per path, download it, and cut a **10–15 sec** snippet (the most characteristic moment) with `ffmpeg`. Save as `docs/demo/snippet-human.wav`, `snippet-ivr-simple.wav`, `snippet-ivr-hard.wav`, `snippet-bot.wav`.
- Keep each snippet short — the point is *range*, not detail.

### 3b. Video — MUST be recorded (does not exist yet)
- **What:** one clean screen recording of the app doing a full run.
- **How:** QuickTime (⌘⇧5 → Record Selected Portion) over the browser window. ~30–45s raw; narrate live over it.
- **Steps to capture** — *matches the real `App.jsx` UI; there is no auto-dispatch:*
  1. App open at the form (Vivant Downtime Check). Note: the form has **12 fields + a checkbox**, first field is **"Location Name"** — pre-fill fast or narrate over it; don't dwell.
  2. Fill the form with the **gauntlet scenario** (Vivant Corp, 2727 Linden, Dallas) so audio + video + report match.
  3. Click **"Save request"** (the form's submit button) → the request appears as a row in the **Saved requests** table below.
  4. On that row, click **"Dispatch Agent"** → status badge flips to **Calling…**.
  5. **Wait for the call to finish** (status leaves `calling`) — *"Get Report" is disabled while `calling`*. Stub/pre-seeded DB makes this near-instant.
  6. Click **"Get Report"** → report card appears (outcome, ETA 8 PM, ticket 55432, transcript, recording).
  7. Stop. Save as `docs/demo/app-run.mov` (or `.mp4`).
- **Mode:** run in **fake-phone / Stub mode** (no `VAPI_API_KEY`) OR pre-seed `outage.db` so the result is instant and deterministic — no live-call risk, and step 5's wait is trivial.
- **Record muted**, narrate live → full control of pacing.
- *(Optional)* a short "ticket/CSV" framing shot to sell the "triggered by a Utiliko ticket" production story.

---

## 4. Build steps (when approved — not now)

1. Create `docs/demo/` and copy in: trimmed audio clip, full WAV, `audio-poster.png`, the 4 montage snippets, the screen-recording video, and an architecture diagram (SVG).
2. Trim the audio highlight (`ffmpeg`), based on cut points from `full_transcript.txt`. **Also build the 4 breadth-montage snippets** (see §3a-bis): download the chosen recordings from the DB and cut 10–15 sec each.
3. Write `docs/demo/demo.html` — self-contained vanilla-JS deck:
   - keyboard nav (← →), slide numbers, progress bar;
   - Vivant brand colors pulled from the app's CSS;
   - embedded `<audio controls>` (poster) + `<video controls muted>`;
   - the **report card rendered as live HTML** (crisp on any projector, not a screenshot);
   - an **on-screen transcript synced to the audio** on slide 6 (see §3a);
   - **per-slide speaker notes** (hidden presenter notes — toggle with a key, or a `?notes` / presenter view) so the presenter knows exactly what to say on each slide;
   - copy reused from `make_deck.py` for consistency — **use "49 tests" (README), not "50" (make_deck.py drift); fix the deck if needed.**
4. Wire the `<video>` slot to `app-run.mov` with a "drop file here" placeholder until the recording exists.
5. Add an **appendix slide (out of the linear 15-min flow)** with the agent's actual prompt from `docs/vapi-config/outage-agent.md` — for the "what's the agent really doing?" Q&A.
6. Smoke-test: opens offline (`file://`) in Chrome + Safari; audio/video play; nav works.

---

## 5. Open items / to decide

**🚧 Must answer before building (the two bookends — the hook and the payoff):**
- [ ] **Problem stat for slide 2** — a defensible number (e.g. "20–40 min/call × N sites/week"). This is the hook; can't be left blank.
- [ ] **Closing ask for slide 11** — the single concrete outcome the talk should drive (funding? a pilot? sign-off to call real ISPs?). This is the payoff.

**Lower-priority / can decide during build:**
- [ ] Record `app-run.mov` (the one manual task on the user's side — see §3b).
- [ ] Whether to trim the audio at all vs. play the full ~3.2 min.
- [ ] **Pick which DB recording represents each montage path** (human / simple IVR / hard IVR / bot) and download them before the Vapi URLs expire (§3a-bis).
- [ ] Whether to include the optional "ticket/CSV" framing shot.

---

## 6. Deliverables

- `docs/demo/demo.html` — the presentation (run it, present it, share it), **with per-slide speaker notes built in**.
- `docs/demo/` — all embedded assets (audio clip, full WAV, video, poster, diagram).
- Works offline; no build step; no dependencies.

---

## 8. Expert feedback — adopted vs. set aside

An expert reviewer offered structuring advice. How it was reconciled:

**Adopted:**
- **4-act structure** (Problem → Solution & how it works → Live demo → Conclusion & future work) — now the spine of §2.
- **Per-slide speaker notes** — decision #8; built into the HTML.
- **Auto-linked video/image placeholders in a named folder** — already §4 (the `app-run.mov` drop-in).
- **2–3 min narrated screen recording showing the end-to-end flow** (enter outage → dispatch → call → results) — §3b/slide 5, widened to show the call step.
- **Demo shows final execution, not the backend setup** — matches §7; the 20-hr Vapi/Twilio/LiveKit debugging story is *not* shown.

**Considered but set aside (audience-dependent):**
- **"Technical audience, 20–25 min, ~10 slides, show the architecture / how Vapi connects"** — the reviewer assumed a *technical* audience. This talk targets the **MSP business buyer** (decision #7), so we keep 15 min and the "hide the plumbing" stance (§7). If a technical version is needed later, the swap is: lengthen to ~22 min, promote the Vapi/Twilio/LiveKit engineering from appendix to a featured "engineering rigor" act.
- **AI-synthesized audio narration of the slides** — deferred (decision #8); useful only for an async/recorded version.

---

## 7. What about showing Vapi / Twilio? (decided: NO walkthrough)

**Decision:** do **not** demo the voice-platform plumbing. It would contradict our own thesis (slide 3 / README: *"the AI call is commoditized — the moat is the structured report"*) and burn minutes an MSP-owner audience doesn't care about. The evaluation agent reached the same conclusion independently.

- **Vapi** → appears as **one line on the architecture slide (#4):** *"Voice runs on Vapi, behind a swappable `VoiceProvider` interface — a choice, not a lock-in (Bland AI drops in; per-ISP routing later)."* This turns the dependency into a moat point. No dashboard walkthrough.
- **Twilio** → **one line on the test slide (#9):** *"We built our own branching IVRs and conversational bots on Twilio to stress-test the agent before touching a real ISP."* A credibility/rigor point, not a demo. (Twilio's other role — provisioning test ISP sites / the no-cap outbound number — is an implementation detail, Q&A only.)
- **Q&A backups (not in the linear flow):**
  - The agent's real prompt → appendix slide from `docs/vapi-config/outage-agent.md`.
  - Vapi daily-cap → imported Twilio number workaround (`make_deck.py:274`).

**Net:** Vapi + Twilio = two sentences in the deck + a hidden appendix. The hero demo stays the app run (video) + the real call (audio) + the report.
