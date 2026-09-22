"""
Chrome DevTools Protocol live network capture.

Connects to a Chromium instance launched with ``--remote-debugging-port``
and subscribes to ``Network.responseReceived`` / ``Network.loadingFinished``
events, turning each finished request into a HAR-shaped entry.

Requires ``websocket-client`` for the CDP WebSocket transport.
"""

import json
import time
import urllib.request
from typing import Any, Dict, List, Optional


def _import_websocket():
    try:
        import websocket
    except ImportError as error:
        raise RuntimeError(
            "websocket-client is required for the CDP capture; "
            "install with: pip install websocket-client"
        ) from error
    return websocket


def discover_targets(devtools_url: str = "http://127.0.0.1:9222") -> List[Dict[str, Any]]:
    """List CDP targets (open tabs)."""
    with urllib.request.urlopen(  # noqa: S310  # nosec B310
        f"{devtools_url.rstrip('/')}/json/list", timeout=5.0,
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def _send(ws, msg_id: int, method: str, params: Optional[Dict[str, Any]] = None) -> None:
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))


def capture_cdp_session(
    target_ws_url: str,
    duration_seconds: float = 30.0,
    timeout_seconds: float = 1.0,
) -> List[Dict[str, Any]]:
    """Subscribe to network events on a CDP target, return HAR entries."""
    websocket_mod = _import_websocket()
    ws = websocket_mod.create_connection(target_ws_url, timeout=timeout_seconds)
    requests_by_id: Dict[str, Dict[str, Any]] = {}
    entries: List[Dict[str, Any]] = []
    _send(ws, 1, "Network.enable")

    deadline = time.monotonic() + duration_seconds
    msg_id = 2
    while time.monotonic() < deadline:
        try:
            ws.settimeout(timeout_seconds)
            raw = ws.recv()
        except websocket_mod.WebSocketTimeoutException:
            continue
        except Exception:  # noqa: BLE001
            break
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        method = event.get("method")
        params = event.get("params") or {}
        if method == "Network.requestWillBeSent":
            req = params.get("request") or {}
            requests_by_id[params["requestId"]] = {
                "startedDateTime": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "request": {
                    "method": req.get("method", "GET"),
                    "url": req.get("url", ""),
                    "headers": [{"name": k, "value": v}
                                for k, v in (req.get("headers") or {}).items()],
                    "postData": {"text": req.get("postData", "")},
                },
            }
        elif method == "Network.responseReceived":
            pending = requests_by_id.get(params["requestId"])
            if pending is None:
                continue
            res = params.get("response") or {}
            pending["response"] = {
                "status": res.get("status", 0),
                "statusText": res.get("statusText", ""),
                "headers": [{"name": k, "value": v}
                            for k, v in (res.get("headers") or {}).items()],
                "content": {"size": 0, "mimeType": res.get("mimeType", "")},
            }
        elif method == "Network.loadingFinished":
            entry = requests_by_id.pop(params["requestId"], None)
            if entry is not None and "response" in entry:
                entry["time"] = int(params.get("encodedDataLength", 0))
                entries.append(entry)
        msg_id += 1
    try:
        ws.close()
    except Exception:  # noqa: BLE001
        pass
    return entries


def capture_cdp_to_har(
    target_ws_url: str,
    output_path: str,
    duration_seconds: float = 30.0,
) -> str:
    """Capture network events and write a HAR file. Returns the path."""
    entries = capture_cdp_session(target_ws_url, duration_seconds=duration_seconds)
    document = {
        "log": {
            "version": "1.2",
            "creator": {"name": "loaddensity-cdp", "version": "1.0"},
            "entries": entries,
        }
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
    return output_path
