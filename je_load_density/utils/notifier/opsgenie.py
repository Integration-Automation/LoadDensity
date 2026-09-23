"""
Opsgenie alert notifier.

Posts an alert when the LoadDensity summary indicates a regression.
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional


def _require_http_scheme(url: str) -> None:
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported notifier scheme: {scheme!r}")


def build_opsgenie_alert(
    summary: Dict[str, Any],
    message: str = "LoadDensity SLA breach",
    priority: str = "P3",
    source: str = "loaddensity",
) -> Dict[str, Any]:
    totals = summary.get("totals", {})
    latency = summary.get("latency_overall", {})
    return {
        "message": message,
        "alias": "loaddensity-sla",
        "description": (
            f"requests={totals.get('requests', 0)}, "
            f"failures={totals.get('failures', 0)}, "
            f"failure_rate={totals.get('failure_rate', 0):.2%}, "
            f"p95={latency.get('p95_ms', 0):.0f}ms"
        ),
        "priority": priority,
        "source": source,
        "tags": ["loaddensity", "load-test"],
    }


def _default_poster(url: str, body: bytes, headers: Dict[str, str], timeout: float) -> int:
    _require_http_scheme(url)
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return response.status


def post_opsgenie_alert(
    api_key: str,
    summary: Optional[Dict[str, Any]] = None,
    message: str = "LoadDensity SLA breach",
    priority: str = "P3",
    api_url: str = "https://api.opsgenie.com/v2/alerts",
    timeout: float = 5.0,
    poster: Callable[[str, bytes, Dict[str, str], float], int] = _default_poster,
) -> int:
    """Build an Opsgenie alert and POST it. Returns HTTP status."""
    if summary is None:
        from je_load_density.utils.generate_report.generate_summary_report import (
            build_summary,
        )
        summary = build_summary()
    payload = build_opsgenie_alert(summary, message=message, priority=priority)
    headers = {
        "Authorization": f"GenieKey {api_key}",
        "Content-Type": "application/json",
    }
    return poster(api_url, json.dumps(payload).encode("utf-8"), headers, timeout)
