"""
AWS Signature Version 4 signer.

Computes the canonical request, string-to-sign, signing key, and final
``Authorization`` header for an AWS service request. Returns a copy of
the headers with the signing material applied.

No third-party SDK required — pure stdlib (``hashlib``, ``hmac``).
"""

import datetime as _dt
import hashlib
import hmac
import urllib.parse
from typing import Dict, Mapping, Optional, Tuple, Union


_EMPTY_HASH = hashlib.sha256(b"").hexdigest()


def _sha256_hex(value: Union[bytes, str]) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _derive_signing_key(secret_key: str, date_stamp: str,
                         region: str, service: str) -> bytes:
    k_date    = _hmac(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region  = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    return _hmac(k_service, "aws4_request")


def _canonical_query(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    encoded = [
        (urllib.parse.quote(key, safe="-_.~"),
         urllib.parse.quote(value, safe="-_.~"))
        for key, value in items
    ]
    encoded.sort()
    return "&".join(f"{k}={v}" for k, v in encoded)


def _canonical_path(url: str) -> str:
    path = urllib.parse.urlparse(url).path or "/"
    return urllib.parse.quote(path, safe="/-_.~")


def _canonical_headers(headers: Mapping[str, str]) -> Tuple[str, str]:
    normalised = {k.lower().strip(): " ".join(str(v).split())
                  for k, v in headers.items()}
    sorted_items = sorted(normalised.items())
    canonical = "".join(f"{k}:{v}\n" for k, v in sorted_items)
    signed = ";".join(name for name, _ in sorted_items)
    return canonical, signed


def sign_aws_request(
    method: str,
    url: str,
    region: str,
    service: str,
    access_key: str,
    secret_key: str,
    body: Union[bytes, str] = b"",
    headers: Optional[Mapping[str, str]] = None,
    session_token: Optional[str] = None,
    now: Optional[_dt.datetime] = None,
) -> Dict[str, str]:
    """
    Return a new headers dict carrying the SigV4 ``Authorization``
    header, ``x-amz-date``, optional ``x-amz-security-token``, and
    ``x-amz-content-sha256``.
    """
    body_bytes = body.encode("utf-8") if isinstance(body, str) else body
    payload_hash = _sha256_hex(body_bytes) if body_bytes else _EMPTY_HASH
    when = now or _dt.datetime.now(_dt.timezone.utc)
    amz_date = when.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = when.strftime("%Y%m%d")

    host = urllib.parse.urlparse(url).netloc
    base_headers: Dict[str, str] = dict(headers or {})
    base_headers.setdefault("host", host)
    base_headers["x-amz-date"] = amz_date
    base_headers["x-amz-content-sha256"] = payload_hash
    if session_token:
        base_headers["x-amz-security-token"] = session_token

    canonical_headers, signed_headers = _canonical_headers(base_headers)
    canonical_request = "\n".join([
        method.upper(),
        _canonical_path(url),
        _canonical_query(url),
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256",
        amz_date,
        credential_scope,
        _sha256_hex(canonical_request),
    ])

    signing_key = _derive_signing_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key,
                          string_to_sign.encode("utf-8"),
                          hashlib.sha256).hexdigest()

    authorization = (
        f"AWS4-HMAC-SHA256 "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    base_headers["Authorization"] = authorization
    return base_headers
