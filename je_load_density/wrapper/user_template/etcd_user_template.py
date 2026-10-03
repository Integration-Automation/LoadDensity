"""
etcd user template (etcd3gw, with legacy etcd3 compatibility; lazy import).

Each task entry::

    {"method": "connect", "host": "127.0.0.1", "port": 2379}
    {"method": "put",  "key": "k", "value": "v"}
    {"method": "get",  "key": "k"}
    {"method": "delete", "key": "k"}
    {"method": "close"}
"""

from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)


def _import_etcd3():
    try:
        import etcd3gw
        return etcd3gw
    except ImportError:
        pass
    try:
        import etcd3
    except ImportError as error:
        raise RuntimeError(
            "etcd3gw is required for EtcdUser; install with: pip install etcd3gw"
        ) from error
    return etcd3


class EtcdUserWrapper(ProtocolUserBase):
    """Locust user driving etcd v3 KV calls."""

    _proxy_key = "etcd_user"
    _request_type = "ETCD"
    host = "127.0.0.1"

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None
        self._gateway_client = False

    def _connect(self, step: Dict[str, Any]) -> int:
        etcd3 = _import_etcd3()
        self._gateway_client = etcd3.__name__ == "etcd3gw"
        self._client = etcd3.client(
            host=step.get("host", self.host),
            port=int(step.get("port", 2379)),
        )
        return 0

    def _put(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("etcd not connected")
        value = step.get("value", "")
        if not isinstance(value, (bytes, str)):
            value = str(value)
        self._client.put(step["key"], value)
        return len(value) if isinstance(value, (bytes, str)) else 0

    def _get(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("etcd not connected")
        result = self._client.get(step["key"])
        if self._gateway_client:
            value = result[0] if result else None
        else:
            value = result[0]
        return len(value or b"")

    def _delete(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("etcd not connected")
        self._client.delete(step["key"])
        return 0

    def _close(self, _: Dict[str, Any]) -> int:
        if self._client is not None:
            if self._gateway_client:
                self._client.session.close()
            else:
                self._client.close()
            self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "put": self._put,
            "get": self._get,
            "delete": self._delete,
            "close": self._close,
        }.get(method)


set_wrapper_etcd_user = make_setter("etcd_user", EtcdUserWrapper)
