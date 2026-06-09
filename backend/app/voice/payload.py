"""Builds the "order form" we hand to the voice provider to start a call.

This packages the destination number, the business details, the agent's
behavior rules (learned from the AT&T baseline call), and any per-ISP hints.
"""

from app.models import OutageRequest

# Short behavior rules — from the AT&T baseline lessons (plan §7), now tone-adaptive.
AGENT_RULES = [
    "Adapt your tone: with an automated system (IVR/recording/bot), be brief and "
    "key-word-first ('Internet outage.'). With a real human, be natural, warm, and "
    "polite in full sentences — never sound robotic with a person.",
    "No filler with machines (skip 'absolutely', 'I appreciate that'); normal courtesy with humans.",
    "If a prompt repeats, change strategy — ask for a representative.",
    "Decline 'can I text you a link' offers; you need the answer on the phone now.",
    "Goal: find out if there is an outage, the reason, and the ETA if given.",
    "Never invent an ETA or reference number. If not given, report 'not provided'.",
]

# Per-ISP navigation hints (plan §7.5). Grows over time, one ISP at a time.
ISP_HINTS = {
    "cox": (
        "Cox: enter the 10-digit phone number for account match; verify street "
        "number + 4-digit PIN. Choose tech support -> internet. During an outage "
        "you reach an automated message with the reason + ETA; usually no human."
    ),
    "at&t": (
        "AT&T: the IVR is a talking bot — answer with one short phrase. It loops "
        "on self-service; decline the text and say 'speak to a technical support "
        "representative'. Say 'business' when asked the account type."
    ),
    "att": (
        "AT&T: the IVR is a talking bot — answer with one short phrase. It loops "
        "on self-service; decline the text and say 'speak to a technical support "
        "representative'. Say 'business' when asked the account type."
    ),
}


def build_call_payload(request: OutageRequest) -> dict:
    """Turn a saved outage request into the payload the provider needs."""
    isp_key = (request.isp_name or "").strip().lower()
    opening = (
        "Our team already checked the equipment; please skip troubleshooting."
        if request.use_equipment_checked_opening
        else ""
    )
    return {
        "destination_number": request.isp_phone,
        "variables": {
            "business_name": request.business_name,
            "business_address": request.business_address,
            "account_number": request.account_number,
            "pin": request.pin,
            "isp_name": request.isp_name or "",
            "caller_name": request.caller_name or "",
            "location_phone": request.location_phone or "",
            "circuit_id": request.circuit_id or "",
            "callback_number": request.callback_number or "",
            "symptoms": request.symptoms or "",
            "troubleshooting_done": request.troubleshooting_done or "",
            "modem_light_status": request.modem_light_status or "",
        },
        "agent_rules": AGENT_RULES,
        "isp_hint": ISP_HINTS.get(isp_key, ""),
        "optional_opening": opening,
    }
