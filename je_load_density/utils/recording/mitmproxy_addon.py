"""
mitmproxy addon — record live traffic straight into a HAR-shaped JSON
which can then feed ``har_to_action_json``.

Run with::

    mitmproxy -s je_load_density/utils/recording/mitmproxy_addon.py \\
              --set ld_har=/tmp/capture.har \\
              --set ld_filter=api\\.example\\.com

Then::

    from je_load_density import load_har, har_to_action_json
    action = har_to_action_json(load_har("/tmp/capture.har"))
"""

import base64
import json
import re
import threading
import time
from typing import Any, Dict, List, Optional


class _State:
    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []
        self.har_path: Optional[str] = None
        self.url_filter: Optional[re.Pattern] = None
        self.lock = threading.Lock()


_state = _State()


def _start_iso(timestamp: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(timestamp))


def _format_request(flow_request) -> Dict[str, Any]:
    return {
        "method": flow_request.method,
        "url": flow_request.url,
        "httpVersion": flow_request.http_version,
        "headers": [{"name": k, "value": v} for k, v in flow_request.headers.items()],
        "queryString": [],
        "headersSize": -1,
        "bodySize": len(flow_request.content or b""),
        "postData": {
            "mimeType": flow_request.headers.get("content-type", ""),
            "text": (flow_request.content or b"").decode("utf-8", errors="replace"),
        },
    }


def _format_response(flow_response) -> Dict[str, Any]:
    body = flow_response.content or b""
    return {
        "status": flow_response.status_code,
        "statusText": flow_response.reason,
        "httpVersion": flow_response.http_version,
        "headers": [{"name": k, "value": v} for k, v in flow_response.headers.items()],
        "content": {
            "size": len(body),
            "mimeType": flow_response.headers.get("content-type", ""),
            "text": base64.b64encode(body).decode("ascii"),
            "encoding": "base64",
        },
        "redirectURL": "",
        "headersSize": -1,
        "bodySize": len(body),
    }


def _persist(entries: List[Dict[str, Any]], path: str) -> None:
    document = {
        "log": {
            "version": "1.2",
            "creator": {"name": "loaddensity-mitmproxy-addon", "version": "1.0"},
            "entries": entries,
        }
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)


# mitmproxy callbacks ----------------------------------------------------------


def load(loader) -> None:  # noqa: D401 - mitmproxy hook signature
    loader.add_option(
        name="ld_har",
        typespec=Optional[str],
        default=None,
        help="HAR file to write captured flows into",
    )
    loader.add_option(
        name="ld_filter",
        typespec=Optional[str],
        default=None,
        help="Regex applied to flow URLs; only matches are captured",
    )


def configure(updates) -> None:  # noqa: D401 - mitmproxy hook
    from mitmproxy import ctx  # type: ignore

    with _state.lock:
        _state.har_path = ctx.options.ld_har
        pattern = ctx.options.ld_filter
        _state.url_filter = re.compile(pattern) if pattern else None


def response(flow) -> None:  # noqa: D401 - mitmproxy hook
    with _state.lock:
        if _state.url_filter and not _state.url_filter.search(flow.request.url):
            return
        _state.entries.append({
            "startedDateTime": _start_iso(flow.request.timestamp_start),
            "time": int((flow.response.timestamp_end - flow.request.timestamp_start) * 1000),
            "request": _format_request(flow.request),
            "response": _format_response(flow.response),
            "cache": {},
            "timings": {"send": 0, "wait": 0, "receive": 0},
        })


def done() -> None:  # noqa: D401 - mitmproxy hook
    with _state.lock:
        if _state.har_path:
            _persist(_state.entries, _state.har_path)
