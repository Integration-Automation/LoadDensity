"""
PII anonymizer — replace common PII patterns in strings or nested dicts.

Pure regex, stdlib only. Designed to scrub captured HAR / replay data
before checking it into version control.
"""

import hashlib
import re
from typing import Any, Iterable

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b\+?\d[\d \-]{7,}\b")
_CREDIT_RE = re.compile(r"\b(?:\d[ \-]?){13,19}\b")
_IPV4_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
_TOKEN_KEY_RE = re.compile(r"(?i)(token|secret|password|api[_-]?key)")


def _stable_replace(prefix: str, value: str) -> str:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=4).hexdigest()
    return f"{prefix}_{digest}"


def scrub_string(text: str) -> str:
    """Replace PII tokens in a single string."""
    if not text:
        return text
    text = _EMAIL_RE.sub(lambda match: _stable_replace("email", match.group(0)), text)
    text = _PHONE_RE.sub(lambda match: _stable_replace("phone", match.group(0)), text)
    text = _CREDIT_RE.sub(lambda match: _stable_replace("card", match.group(0)), text)
    text = _IPV4_RE.sub(lambda match: _stable_replace("ip", match.group(0)), text)
    return text


def scrub(value: Any) -> Any:
    """Recursively scrub strings and dict values."""
    if isinstance(value, str):
        return scrub_string(value)
    if isinstance(value, dict):
        return {
            key: (
                _stable_replace("secret", str(inner))
                if isinstance(key, str) and _TOKEN_KEY_RE.search(key) and isinstance(inner, str)
                else scrub(inner)
            )
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value


def find_pii(text: str) -> Iterable[str]:
    """Yield PII tokens found in text (useful for spot-checking before scrub)."""
    for match in _EMAIL_RE.finditer(text or ""):
        yield match.group(0)
    for match in _PHONE_RE.finditer(text or ""):
        yield match.group(0)
    for match in _CREDIT_RE.finditer(text or ""):
        yield match.group(0)
