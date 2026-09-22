"""
HashiCorp Vault user template (HTTP API via stdlib urllib, no extra dep).

Each task entry::

    {"method": "read",  "path": "secret/data/myapp",
     "addr": "https://127.0.0.1:8200", "token": "${env.VAULT_TOKEN}"}
    {"method": "write", "path": "secret/data/myapp",
     "data": {"data": {"k": "v"}}}
    {"method": "delete", "path": "secret/data/myapp"}
    {"method": "list", "path": "secret/metadata"}
"""

import json
import urllib.request
from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)

_DEFAULT_ADDR = "https://127.0.0.1:8200"


def _request(
    method: str,
    url: str,
    token: str,
    body: Optional[bytes],
    timeout: float,
) -> bytes:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return response.read()


def _url(step: Dict[str, Any]) -> str:
    addr = step.get("addr", _DEFAULT_ADDR).rstrip("/")
    return f"{addr}/v1/{step['path'].lstrip('/')}"


class VaultUserWrapper(ProtocolUserBase):
    """Locust user driving Vault HTTP API calls."""

    _proxy_key = "vault_user"
    _request_type = "VAULT"
    host = _DEFAULT_ADDR

    def _read(self, step: Dict[str, Any]) -> int:
        data = _request(
            "GET", _url(step), str(step.get("token", "")), None,
            float(step.get("timeout", 5.0)),
        )
        return len(data)

    def _write(self, step: Dict[str, Any]) -> int:
        body = json.dumps(step.get("data") or {}).encode("utf-8")
        _request(
            "POST", _url(step), str(step.get("token", "")), body,
            float(step.get("timeout", 5.0)),
        )
        return len(body)

    def _delete(self, step: Dict[str, Any]) -> int:
        _request(
            "DELETE", _url(step), str(step.get("token", "")), None,
            float(step.get("timeout", 5.0)),
        )
        return 0

    def _list(self, step: Dict[str, Any]) -> int:
        data = _request(
            "LIST", _url(step), str(step.get("token", "")), None,
            float(step.get("timeout", 5.0)),
        )
        return len(data)

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "read": self._read,
            "write": self._write,
            "delete": self._delete,
            "list": self._list,
        }.get(method)


set_wrapper_vault_user = make_setter("vault_user", VaultUserWrapper)
