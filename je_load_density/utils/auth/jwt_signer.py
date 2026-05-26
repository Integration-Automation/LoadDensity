"""
JWT signer (HS256, HS384, HS512, RS256, RS384, RS512).

No third-party JWT library; uses the stdlib ``hmac`` and ``hashlib``
for HS, and ``cryptography`` (soft-dep) for RS.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Tuple, Union


_HMAC_ALGS = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}

_RSA_HASHES = {
    "RS256": "SHA-256",
    "RS384": "SHA-384",
    "RS512": "SHA-512",
}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _hmac_sign(message: bytes, secret: Union[str, bytes], hasher) -> bytes:
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    return hmac.new(key, message, hasher).digest()


def _rsa_sign(message: bytes, private_key: Union[str, bytes], algorithm: str) -> bytes:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as error:
        raise RuntimeError(
            "cryptography is required for RS* algorithms; install with: pip install cryptography"
        ) from error
    pem = private_key.encode("utf-8") if isinstance(private_key, str) else private_key
    key = serialization.load_pem_private_key(pem, password=None)
    hash_name = _RSA_HASHES[algorithm].replace("-", "")
    hash_cls = getattr(hashes, hash_name)
    return key.sign(message, padding.PKCS1v15(), hash_cls())


def sign_jwt(
    payload: Dict[str, Any],
    secret: Union[str, bytes],
    algorithm: str = "HS256",
    headers: Optional[Dict[str, Any]] = None,
    expires_in_seconds: Optional[int] = None,
) -> str:
    """
    Build and sign a JSON Web Token. Mutates a copy of ``payload`` —
    if ``expires_in_seconds`` is set, ``exp`` is added.
    """
    final_payload = dict(payload)
    if expires_in_seconds is not None and "exp" not in final_payload:
        final_payload["exp"] = int(time.time()) + int(expires_in_seconds)

    final_headers = {"alg": algorithm, "typ": "JWT"}
    if headers:
        final_headers.update(headers)

    header_segment = _b64url_encode(json.dumps(final_headers, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(final_payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")

    hasher = _HMAC_ALGS.get(algorithm)
    if hasher is not None:
        signature = _hmac_sign(signing_input, secret, hasher)
    elif algorithm in _RSA_HASHES:
        signature = _rsa_sign(signing_input, secret, algorithm)
    else:
        raise ValueError(f"unsupported JWT algorithm: {algorithm}")

    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def decode_jwt(token: str) -> Tuple[Dict[str, Any], Dict[str, Any], bytes]:
    """
    Decode the three JWT segments *without* verifying the signature.
    Returns ``(header_dict, payload_dict, signature_bytes)``.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid JWT: expected 3 dot-separated segments")
    header = json.loads(_b64url_decode(parts[0]))
    payload = json.loads(_b64url_decode(parts[1]))
    signature = _b64url_decode(parts[2])
    return header, payload, signature
