# Test IVR (Twilio) — AT&T-style outage line (2 menu levels)

Tests the agent navigating a real phone menu (DTMF / keypad). The agent calls
the Twilio number → main menu (press 2 for support/outages) → account-type menu
(press 2 for business) → recorded outage message with reason, ETA, reference #.

**Three TwiML Bins. Build deepest-first** so each one's URL is ready for the menu
above it: Outage Status → Account Type → Main Menu.

---

## Bin 3 — "Outage Status" (create FIRST — the result)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">Thank you. One moment while I check our systems.</Say>
  <Pause length="2"/>
  <Say voice="Polly.Joanna">Yes, A T and T is aware of an internet outage affecting your area. It was caused by a fiber cut. The estimated restoration time is 6 P M today. Your reference number is 1 2 3 4 5. Is there anything else? If not, goodbye.</Say>
  <Hangup/>
</Response>
```
→ Save, copy this bin's URL (call it **URL_3**).

---

## Bin 2 — "Account Type" (create SECOND; action = URL_3)

Replace `PASTE_OUTAGE_STATUS_URL` with **URL_3**.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather numDigits="1" timeout="10" action="PASTE_OUTAGE_STATUS_URL">
    <Say voice="Polly.Joanna">Is this a personal or a business account? For a personal account, press 1. For a business account, press 2.</Say>
  </Gather>
  <Say voice="Polly.Joanna">Sorry, we did not get your selection. Goodbye.</Say>
  <Hangup/>
</Response>
```
→ Save, copy this bin's URL (call it **URL_2**).

---

## Bin 1 — "Main Menu" (create THIRD; action = URL_2)

Replace `PASTE_ACCOUNT_TYPE_URL` with **URL_2**.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather numDigits="1" timeout="10" action="PASTE_ACCOUNT_TYPE_URL">
    <Say voice="Polly.Joanna">Thank you for calling A T and T business services. For sales, press 1. For technical support and internet outages, press 2.</Say>
  </Gather>
  <Say voice="Polly.Joanna">Sorry, we did not get your selection. Goodbye.</Say>
  <Hangup/>
</Response>
```

---

## Wiring
- Point the Twilio number's **"A call comes in"** voice webhook to **Bin 1 (Main Menu)**.
- Flow: call → Main Menu (press 2) → Account Type (press 2) → Outage Status → hang up.

## Known limitation (revisit later)
This Twilio IVR is **keypad-only** — it plays prompts and hangs up; it **cannot
hold a two-way conversation** (e.g. ask "anything else?" and actually listen).
That's fine for testing **DTMF navigation**. To test the **conversational** ISP
case (like AT&T's talking bot, with self-service loops + callback), build a
**second AI assistant** that role-plays the ISP — see Future Works (§12.5,
"Per-ISP provider routing" / agent eval).
