"""
Microsoft Teams notifier.

Builds a connector-card payload (legacy MessageCard schema; widely
supported by Office 365 webhooks) and POSTs it.
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional


def _require_http_scheme(url: str) -> None:
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported webhook scheme: {scheme!r}")


def build_teams_summary(summary: Dict[str, Any], title: str = "LoadDensity run") -> Dict[str, Any]:
    totals = summary.get("totals", {})
    latency = summary.get("latency_overall", {})
    facts = [
        {"name": "Requests", "value": str(totals.get("requests", 0))},
        {"name": "Failures", "value": str(totals.get("failures", 0))},
        {"name": "Failure rate", "value": f"{totals.get('failure_rate', 0):.2%}"},
        {"name": "P95 latency", "value": f"{latency.get('p95_ms', 0):.0f} ms"},
    ]
    return {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": title,
        "themeColor": "0072C6",
        "title": title,
        "sections": [{"facts": facts, "markdown": True}],
    }


def _default_poster(url: str, body: bytes, timeout: float) -> int:
    _require_http_scheme(url)
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return response.status


def post_teams_summary(
    webhook_url: str,
    summary: Optional[Dict[str, Any]] = None,
    title: str = "LoadDensity run",
    timeout: float = 5.0,
    poster: Callable[[str, bytes, float], int] = _default_poster,
) -> int:
    if summary is None:
        from je_load_density.utils.generate_report.generate_summary_report import (
            build_summary,
        )
        summary = build_summary()
    payload = build_teams_summary(summary, title=title)
    return poster(webhook_url, json.dumps(payload).encode("utf-8"), timeout)
