"""
Memcached user template (pymemcache, lazy import).

Each task entry::

    {"method": "connect", "host": "127.0.0.1", "port": 11211}
    {"method": "set", "key": "k", "value": "v"}
    {"method": "get", "key": "k"}
    {"method": "delete", "key": "k"}
    {"method": "close"}
"""

from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)


def _import_pymemcache():
    try:
        from pymemcache.client.base import Client
    except ImportError as error:
        raise RuntimeError(
            "pymemcache is required for MemcachedUser; "
            "install with: pip install pymemcache"
        ) from error
    return Client


class MemcachedUserWrapper(ProtocolUserBase):
    """Locust user driving pymemcache calls."""

    _proxy_key = "memcached_user"
    _request_type = "MEMCACHED"
    host = "127.0.0.1"

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None

    def _connect(self, step: Dict[str, Any]) -> int:
        client_cls = _import_pymemcache()
        host = step.get("host", self.host)
        port = int(step.get("port", 11211))
        self._client = client_cls((host, port))
        return 0

    def _set(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("memcached not connected")
        value = step.get("value", "")
        self._client.set(step["key"], value)
        if isinstance(value, bytes):
            return len(value)
        return len(str(value))

    def _get(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("memcached not connected")
        data = self._client.get(step["key"])
        return len(data) if data else 0

    def _delete(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("memcached not connected")
        self._client.delete(step["key"])
        return 0

    def _close(self, _: Dict[str, Any]) -> int:
        if self._client is not None:
            self._client.close()
            self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "set": self._set,
            "get": self._get,
            "delete": self._delete,
            "close": self._close,
        }.get(method)


set_wrapper_memcached_user = make_setter("memcached_user", MemcachedUserWrapper)
