"""
Consul KV user template (HTTP API via stdlib urllib, no extra dep).

Each task entry::

    {"method": "put",    "key": "config/x", "value": "yes",
     "addr": "http://127.0.0.1:8500"}
    {"method": "get",    "key": "config/x"}
    {"method": "delete", "key": "config/x"}
    {"method": "services"}
"""

import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._common import payload_bytes
from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)

_DEFAULT_ADDR = "http://127.0.0.1:8500"


def _request(method: str, url: str, body: Optional[bytes], timeout: float) -> bytes:
    request = urllib.request.Request(url, data=body, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return response.read()


def _kv_url(step: Dict[str, Any]) -> str:
    addr = step.get("addr", _DEFAULT_ADDR).rstrip("/")
    return f"{addr}/v1/kv/{urllib.parse.quote(step['key'], safe='/')}"


class ConsulUserWrapper(ProtocolUserBase):
    """Locust user driving Consul HTTP KV calls."""

    _proxy_key = "consul_user"
    _request_type = "CONSUL"
    host = _DEFAULT_ADDR

    def _put(self, step: Dict[str, Any]) -> int:
        value = step.get("value", "")
        body = payload_bytes(value)
        _request("PUT", _kv_url(step), body, float(step.get("timeout", 5.0)))
        return len(body)

    def _get(self, step: Dict[str, Any]) -> int:
        data = _request("GET", _kv_url(step), None, float(step.get("timeout", 5.0)))
        return len(data)

    def _delete(self, step: Dict[str, Any]) -> int:
        _request("DELETE", _kv_url(step), None, float(step.get("timeout", 5.0)))
        return 0

    def _services(self, step: Dict[str, Any]) -> int:
        addr = step.get("addr", _DEFAULT_ADDR).rstrip("/")
        data = _request("GET", f"{addr}/v1/agent/services", None,
                        float(step.get("timeout", 5.0)))
        return len(data)

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "put": self._put,
            "get": self._get,
            "delete": self._delete,
            "services": self._services,
        }.get(method)


set_wrapper_consul_user = make_setter("consul_user", ConsulUserWrapper)
