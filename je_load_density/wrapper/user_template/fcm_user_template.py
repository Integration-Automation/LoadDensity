"""
Firebase Cloud Messaging (FCM) HTTP v1 user template.

Stdlib-only (urllib). The caller is responsible for minting an OAuth2
bearer token (use ``OAuth2Client`` or any other means) and passing it as
``token`` on each step.

Each task entry::

    {"method": "send", "project_id": "my-project",
     "token": "ya29...",
     "message": {"token": "device-x", "notification": {"title": "hi"}}}
"""

import json
import urllib.request
from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)


class FcmUserWrapper(ProtocolUserBase):
    """Locust user driving FCM HTTP v1 calls."""

    _proxy_key = "fcm_user"
    _request_type = "FCM"
    host = "https://fcm.googleapis.com"

    def _send(self, step: Dict[str, Any]) -> int:
        url = (
            f"{step.get('endpoint', self.host).rstrip('/')}/v1/projects/"
            f"{step['project_id']}/messages:send"
        )
        body = json.dumps({"message": step.get("message") or {}}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {step['token']}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        timeout = float(step.get("timeout", 10.0))
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
            return len(response.read())

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {"send": self._send}.get(method)


set_wrapper_fcm_user = make_setter("fcm_user", FcmUserWrapper)
