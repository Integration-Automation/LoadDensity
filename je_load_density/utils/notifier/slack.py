"""
Slack notifier.

Builds a Block Kit payload from the LoadDensity summary and POSTs it to
an incoming-webhook URL. Network I/O can be swapped via the ``poster``
parameter so tests don't hit the network.
"""

import json
import urllib.request
from typing import Any, Callable, Dict, Optional


def build_slack_summary(summary: Dict[str, Any], title: str = "LoadDensity run") -> Dict[str, Any]:
    totals = summary.get("totals", {})
    latency = summary.get("latency_overall", {})
    fields = [
        {"type": "mrkdwn", "text": f"*Requests*\n{totals.get('requests', 0)}"},
        {"type": "mrkdwn", "text": f"*Failures*\n{totals.get('failures', 0)}"},
        {"type": "mrkdwn",
         "text": f"*Failure rate*\n{totals.get('failure_rate', 0):.2%}"},
        {"type": "mrkdwn",
         "text": f"*P95 latency*\n{latency.get('p95_ms', 0):.0f} ms"},
    ]
    return {
        "blocks": [
            {"type": "header",
             "text": {"type": "plain_text", "text": title}},
            {"type": "section", "fields": fields},
        ]
    }


def _default_poster(url: str, body: bytes, timeout: float) -> int:
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.status


def post_slack_summary(
    webhook_url: str,
    summary: Optional[Dict[str, Any]] = None,
    title: str = "LoadDensity run",
    timeout: float = 5.0,
    poster: Callable[[str, bytes, float], int] = _default_poster,
) -> int:
    """
    Build a Slack Block Kit message from ``summary`` (defaults to
    ``build_summary()``) and POST it. Returns the HTTP status.
    """
    if summary is None:
        from je_load_density.utils.generate_report.generate_summary_report import (
            build_summary,
        )
        summary = build_summary()
    payload = build_slack_summary(summary, title=title)
    return poster(webhook_url, json.dumps(payload).encode("utf-8"), timeout)
