"""Snapshot the Vapi assistant configs into docs/vapi-config/ so the agent's
'brain' (prompt + settings) is version-controlled. Re-run anytime to refresh.

Usage:  .venv/bin/python ../docs/save_vapi_config.py <VAPI_API_KEY>
"""

import json
import os
import sys
import urllib.request

KEY = sys.argv[1]
OUT = "/Users/mohammadmaydanchi/Documents/vivant_corp/docs/vapi-config"
os.makedirs(OUT, exist_ok=True)

ASSISTANTS = {
    "outage-agent": "36deea65-7718-46f9-ab67-f01fa6125330",
    "test-bot-normal": "7f4aa4af-b7d2-4ba8-925a-29695f0bdf0a",
    "test-bot-hard": "f7f9ad55-7a66-43b9-a2e8-17ece4f3c404",
}

SECRET_HINTS = ("token", "secret", "apikey", "api_key", "authtoken")


def redact(obj):
    """Drop any field that looks like a secret (defensive — configs usually have none)."""
    if isinstance(obj, dict):
        return {
            k: ("***REDACTED***" if any(h in k.lower() for h in SECRET_HINTS) else redact(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj


def get(path):
    req = urllib.request.Request(
        f"https://api.vapi.ai/{path}",
        headers={"Authorization": "Bearer " + KEY, "User-Agent": "curl/8.4.0"},
    )
    return json.load(urllib.request.urlopen(req))


def prompt_of(a):
    msgs = (a.get("model") or {}).get("messages") or []
    return msgs[0].get("content", "") if msgs else ""


for name, aid in ASSISTANTS.items():
    a = get(f"assistant/{aid}")
    json.dump(redact(a), open(f"{OUT}/{name}.json", "w"), indent=2)

    # human-readable summary
    m = a.get("model") or {}
    v = a.get("voice") or {}
    sp = a.get("startSpeakingPlan") or {}
    lines = [
        f"# {a.get('name')} — Vapi config snapshot",
        "",
        f"- **id:** `{a.get('id')}`",
        f"- **model:** {m.get('provider')} / {m.get('model')}",
        f"- **voice:** {v.get('provider')} / {v.get('voiceId') or v.get('voice')}",
        f"- **firstMessageMode:** {a.get('firstMessageMode')}",
        f"- **firstMessage:** {a.get('firstMessage')!r}",
        f"- **silenceTimeoutSeconds:** {a.get('silenceTimeoutSeconds')}",
        f"- **maxDurationSeconds:** {a.get('maxDurationSeconds')}",
        f"- **endCallMessage:** {a.get('endCallMessage')!r}",
        f"- **endCallPhrases:** {a.get('endCallPhrases')}",
        f"- **startSpeakingPlan:** waitSeconds={sp.get('waitSeconds')}, "
        f"smartEndpointing={(sp.get('smartEndpointingPlan') or {}).get('provider')}",
        f"- **tools:** {[ (t.get('type') or t.get('function',{}).get('name')) for t in (a.get('model') or {}).get('tools', []) ]}",
        "",
        "## System prompt",
        "",
        "```",
        prompt_of(a),
        "```",
    ]
    open(f"{OUT}/{name}.md", "w").write("\n".join(lines))

# phone number -> assistant mapping (redacted)
nums = get("phone-number")
mapping = [
    {"number": n.get("number"), "provider": n.get("provider"),
     "id": n.get("id"), "name": n.get("name"), "assistantId": n.get("assistantId")}
    for n in nums
]
json.dump(mapping, open(f"{OUT}/phone-numbers.json", "w"), indent=2)

print("Saved configs for:", ", ".join(ASSISTANTS), "+ phone-numbers")
