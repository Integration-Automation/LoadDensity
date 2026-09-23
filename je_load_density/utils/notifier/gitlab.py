"""
GitLab Merge Request note notifier.

Posts a Markdown comment to a Merge Request with the LoadDensity summary.
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional


def _require_http_scheme(url: str) -> None:
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported notifier scheme: {scheme!r}")


def build_gitlab_mr_note(summary: Dict[str, Any], title: str = "LoadDensity run") -> str:
    totals = summary.get("totals", {})
    latency = summary.get("latency_overall", {})
    return (
        f"### {title}\n\n"
        f"| metric | value |\n"
        f"|---|---|\n"
        f"| requests | {totals.get('requests', 0)} |\n"
        f"| failures | {totals.get('failures', 0)} |\n"
        f"| failure rate | {totals.get('failure_rate', 0):.2%} |\n"
        f"| p95 latency | {latency.get('p95_ms', 0):.0f} ms |\n"
    )


def _default_poster(url: str, body: bytes, headers: Dict[str, str], timeout: float) -> int:
    _require_http_scheme(url)
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return response.status


def post_gitlab_mr_summary(
    project_id: str,
    merge_request_iid: int,
    token: str,
    summary: Optional[Dict[str, Any]] = None,
    base_url: str = "https://gitlab.com/api/v4",
    title: str = "LoadDensity run",
    timeout: float = 5.0,
    poster: Callable[[str, bytes, Dict[str, str], float], int] = _default_poster,
) -> int:
    """POST a Markdown summary note to a GitLab MR. Returns HTTP status."""
    if summary is None:
        from je_load_density.utils.generate_report.generate_summary_report import (
            build_summary,
        )
        summary = build_summary()
    body_text = build_gitlab_mr_note(summary, title=title)
    encoded_project = urllib.parse.quote(str(project_id), safe="")
    api_url = (
        f"{base_url.rstrip('/')}/projects/{encoded_project}/"
        f"merge_requests/{int(merge_request_iid)}/notes"
    )
    payload = json.dumps({"body": body_text}).encode("utf-8")
    headers = {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}
    return poster(api_url, payload, headers, timeout)
