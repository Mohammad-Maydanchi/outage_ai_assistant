"""Webhook signature checking.

Vapi signs each webhook with a shared secret. We recompute the signature over
the exact raw body and compare — if it doesn't match, the request isn't really
from Vapi and we reject it.
"""

import hashlib
import hmac
from typing import Optional


def compute_signature(secret: str, raw_body: bytes) -> str:
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


def verify_signature(secret: str, raw_body: bytes, signature: Optional[str]) -> bool:
    """True only if the signature matches. Empty secret or missing signature = reject."""
    if not secret or not signature:
        return False
    expected = compute_signature(secret, raw_body)
    return hmac.compare_digest(expected, signature)
