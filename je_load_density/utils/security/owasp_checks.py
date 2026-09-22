"""
OWASP API Security Top 10 (2023) lightweight checks.

Each check inspects request + response data captured during a load test
and emits findings. Checks are intentionally heuristic — they flag
suspicious responses so the operator can investigate, not a full DAST.
"""

from typing import Any, Dict, Iterable, List

_SENSITIVE_TOKENS = (
    "password", "secret", "token", "api_key", "apikey",
    "authorization", "ssn", "credit_card",
)


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for inner in value.values():
            yield from _walk_strings(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _walk_strings(inner)


def check_excessive_data_exposure(response_body: Any, fields: List[str]) -> List[Dict[str, Any]]:
    """Flag API responses leaking sensitive field names."""
    findings: List[Dict[str, Any]] = []
    for field in fields:
        for text in _walk_strings(response_body):
            if f'"{field}"' in text or f"'{field}'" in text:
                findings.append({
                    "rule": "owasp.api3.excessive_data_exposure",
                    "field": field,
                    "severity": "warning",
                })
                break
    return findings


def check_broken_object_level_auth(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flag tasks where iterating IDs returns 2xx for multiple users."""
    counts: Dict[str, int] = {}
    for record in records:
        if str(record.get("status_code", ""))[:1] == "2" and "/users/" in str(record.get("name", "")):
            name = str(record.get("name", ""))
            counts[name] = counts.get(name, 0) + 1
    return [
        {
            "rule": "owasp.api1.bola_suspect",
            "endpoint": endpoint,
            "hits": count,
            "severity": "info",
        }
        for endpoint, count in counts.items()
        if count >= 5
    ]


def check_security_headers(headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Flag missing common security response headers."""
    expected = {
        "strict-transport-security": "owasp.api8.missing_hsts",
        "x-content-type-options": "owasp.api8.missing_xcto",
        "content-security-policy": "owasp.api8.missing_csp",
    }
    normalised = {k.lower(): v for k, v in headers.items()}
    findings: List[Dict[str, Any]] = []
    for header_name, rule in expected.items():
        if header_name not in normalised:
            findings.append({
                "rule": rule,
                "header": header_name,
                "severity": "warning",
            })
    return findings


def check_sensitive_token_leak(text: str) -> List[Dict[str, Any]]:
    """Flag occurrences of obvious sensitive tokens in a body or log line."""
    findings: List[Dict[str, Any]] = []
    lower = text.lower()
    for token in _SENSITIVE_TOKENS:
        if token in lower:
            findings.append({
                "rule": "owasp.api3.sensitive_data_in_response",
                "token": token,
                "severity": "warning",
            })
    return findings


def run_owasp_checks(
    response_body: Any,
    headers: Dict[str, str],
    records: Iterable[Dict[str, Any]],
    sensitive_fields: List[str],
) -> List[Dict[str, Any]]:
    """Run every check and return a flat list of findings."""
    findings: List[Dict[str, Any]] = []
    findings.extend(check_excessive_data_exposure(response_body, sensitive_fields))
    findings.extend(check_broken_object_level_auth(records))
    findings.extend(check_security_headers(headers))
    for text in _walk_strings(response_body):
        findings.extend(check_sensitive_token_leak(text))
    return findings
