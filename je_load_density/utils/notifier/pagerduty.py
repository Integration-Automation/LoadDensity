"""
PagerDuty Events API v2 notifier.

Triggers an incident when the LoadDensity summary breaches a threshold;
network I/O is swappable for tests.
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional


def _require_http_scheme(url: str) -> None:
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported notifier scheme: {scheme!r}")


def build_pagerduty_event(
    routing_key: str,
    summary: Dict[str, Any],
    severity: str = "error",
    source: str = "loaddensity",
    title: str = "LoadDensity SLA breach",
) -> Dict[str, Any]:
    totals = summary.get("totals", {})
    latency = summary.get("latency_overall", {})
    return {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": title,
            "severity": severity,
            "source": source,
            "custom_details": {
                "requests": totals.get("requests", 0),
                "failures": totals.get("failures", 0),
                "failure_rate": totals.get("failure_rate", 0),
                "p95_ms": latency.get("p95_ms", 0),
            },
        },
    }


def _default_poster(url: str, body: bytes, timeout: float) -> int:
    _require_http_scheme(url)
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return response.status


def post_pagerduty_event(
    routing_key: str,
    summary: Optional[Dict[str, Any]] = None,
    title: str = "LoadDensity SLA breach",
    severity: str = "error",
    api_url: str = "https://events.pagerduty.com/v2/enqueue",
    timeout: float = 5.0,
    poster: Callable[[str, bytes, float], int] = _default_poster,
) -> int:
    """Build a PagerDuty Events v2 trigger and POST it. Returns HTTP status."""
    if summary is None:
        from je_load_density.utils.generate_report.generate_summary_report import (
            build_summary,
        )
        summary = build_summary()
    payload = build_pagerduty_event(routing_key, summary, severity=severity, title=title)
    return poster(api_url, json.dumps(payload).encode("utf-8"), timeout)
