"""
WebPush user template (pywebpush, lazy import).

Each task entry::

    {"method": "send",
     "subscription": {"endpoint": "https://push.example/...", "keys": {...}},
     "data": "hello",
     "vapid_private_key": "...",
     "vapid_claims": {"sub": "mailto:ops@example"},
     "ttl": 60}
"""

from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)


def _import_pywebpush():
    try:
        from pywebpush import webpush
    except ImportError as error:
        raise RuntimeError(
            "pywebpush is required for WebPushUser; install with: pip install pywebpush"
        ) from error
    return webpush


class WebPushUserWrapper(ProtocolUserBase):
    """Locust user driving pywebpush."""

    _proxy_key = "webpush_user"
    _request_type = "WEBPUSH"

    def _send(self, step: Dict[str, Any]) -> int:
        webpush = _import_pywebpush()
        body = step.get("data", "")
        if not isinstance(body, (str, bytes)):
            import json as json_module
            body = json_module.dumps(body)
        response = webpush(
            subscription_info=step["subscription"],
            data=body,
            vapid_private_key=step.get("vapid_private_key"),
            vapid_claims=step.get("vapid_claims") or {},
            ttl=int(step.get("ttl", 60)),
        )
        return len(getattr(response, "text", "") or "")

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {"send": self._send}.get(method)


set_wrapper_webpush_user = make_setter("webpush_user", WebPushUserWrapper)
