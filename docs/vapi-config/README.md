# Vapi assistant config — version-controlled snapshot

The agent's "brain" (its system prompt, voice, model, and behavior settings)
lives in the **Vapi dashboard**, not in this codebase. If that account is lost
or someone edits it, the tuning is gone. These files snapshot it so it's
**reproducible and reviewable** like the rest of the project.

## Files
| File | What it is |
|------|------------|
| `outage-agent.json` / `.md` | **The product agent** — full config + readable prompt/settings. This is the important one. |
| `test-bot-normal.json` / `.md` | Test rig: the conversational "Fake AT&T Bot". |
| `test-bot-hard.json` / `.md` | Test rig: the "Hard AT&T Bot" (verification gauntlet). |
| `phone-numbers.json` | Which number is answered by which assistant (outbound vs bot lines). |

The `.md` files are for reading; the `.json` files are the exact config.
Secrets are redacted (and assistant configs contain no API keys anyway).

## Refresh the snapshot (after changing anything in Vapi)
```bash
cd backend
.venv/bin/python ../docs/save_vapi_config.py "$(grep '^VAPI_API_KEY=' ../.env | cut -d= -f2-)"
```

## Restore / recreate an assistant in Vapi from a snapshot
1. Vapi → **Create Assistant** → **Blank**.
2. Set **Model** (e.g. OpenAI / gpt-4o-mini) and **Voice** per the `.md` summary.
3. Paste the **System prompt** from the `.md` file.
4. Set **First Message** mode (e.g. agent = "waits for user"), **End Call Message**,
   **End Call Phrases**, **Silence Timeout**, **Max Duration**, and the
   **Start Speaking Plan** (waitSeconds + LiveKit smart endpointing) per the summary.
5. For the agent: attach the **DTMF / "Dial Keypad"** tool (Tools → Select Tools)
   so it can navigate IVR menus.
6. Publish, then point the relevant phone number at it (see `phone-numbers.json`).

> Note: the in-call dynamic variables (`{{business_name}}`, `{{account_number}}`,
> etc.) are supplied at call time by the backend's payload builder
> (`backend/app/voice/payload.py`).
