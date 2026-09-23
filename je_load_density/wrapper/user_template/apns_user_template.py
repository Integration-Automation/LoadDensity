"""
APNS (Apple Push Notification Service) user template via HTTP/2.

Uses httpx (lazy import, http2 extra) to talk to the APNS HTTP/2 endpoint
with a JWT provider auth token.

Each task entry::

    {"method": "send", "device_token": "abc...",
     "topic": "com.example.app",
     "payload": {"aps": {"alert": "hi"}},
     "endpoint": "https://api.sandbox.push.apple.com",
     "jwt": "eyJh..."}
"""

import json as json_module
from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)


def _import_httpx():
    try:
        import httpx
    except ImportError as error:
        raise RuntimeError(
            "httpx is required for ApnsUser; install with: pip install 'httpx[http2]'"
        ) from error
    return httpx


class ApnsUserWrapper(ProtocolUserBase):
    """Locust user driving APNS HTTP/2 calls."""

    _proxy_key = "apns_user"
    _request_type = "APNS"
    host = "https://api.sandbox.push.apple.com"

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None
        self._endpoint: Optional[str] = None

    def _client_for(self, step: Dict[str, Any]):
        """The HTTP/2 client for the step's endpoint; a different endpoint gets a new client."""
        endpoint = step.get("endpoint", self.host)
        if self._client is not None and endpoint != self._endpoint:
            self._client.close()
            self._client = None
        if self._client is None:
            httpx = _import_httpx()
            self._client = httpx.Client(
                http2=True, base_url=endpoint,
                timeout=float(step.get("timeout", 10.0)),
            )
            self._endpoint = endpoint
        return self._client

    def _send(self, step: Dict[str, Any]) -> int:
        client = self._client_for(step)
        body = json_module.dumps(step.get("payload") or {}).encode("utf-8")
        headers = {
            "apns-topic": step.get("topic", ""),
            "content-type": "application/json",
        }
        jwt = step.get("jwt")
        if jwt:
            headers["authorization"] = f"bearer {jwt}"
        device_token = step["device_token"]
        response = client.post(f"/3/device/{device_token}", content=body, headers=headers)
        if response.status_code != 200:
            # APNs answers 200 only on success; anything else carries {"reason": ...} in the body.
            raise RuntimeError(
                f"APNs rejected the notification: HTTP {response.status_code} "
                f"{response.content.decode('utf-8', errors='replace')}"
            )
        return len(response.content)

    def _close(self, _: Dict[str, Any]) -> int:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._endpoint = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {"send": self._send, "close": self._close}.get(method)


set_wrapper_apns_user = make_setter("apns_user", ApnsUserWrapper)
