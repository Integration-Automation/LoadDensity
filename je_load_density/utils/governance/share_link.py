"""
Signed read-only share link generator.

Issues HMAC-signed URLs so the operator can post a public link to a
report without exposing write actions. The verifier resolves the link
back into a report path; expiry is enforced.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def issue_share_link(
    base_url: str,
    report_path: str,
    secret: str,
    expires_in_seconds: int = 86400,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Return ``base_url?token=<signed-token>``."""
    payload = dict(extra_claims or {})
    payload.update({
        "p": report_path,
        "exp": int(time.time()) + max(60, int(expires_in_seconds)),
        "n": secrets.token_hex(8),
    })
    body = _b64url(json.dumps(payload, sort_keys=True).encode("utf-8"))
    signature = _b64url(hmac.new(
        secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256,
    ).digest())
    return f"{base_url.rstrip('/')}?token={body}.{signature}"


def verify_share_link(token: str, secret: str) -> Dict[str, Any]:
    """
    Return the decoded payload on success, raise ``ValueError`` on failure
    (expired, malformed, or bad signature).
    """
    try:
        body, signature = token.split(".", 1)
    except ValueError as error:
        raise ValueError("malformed token") from error
    expected = _b64url(hmac.new(
        secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256,
    ).digest())
    if not hmac.compare_digest(expected, signature):
        raise ValueError("bad signature")
    payload = json.loads(_b64url_decode(body))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("expired token")
    return payload
