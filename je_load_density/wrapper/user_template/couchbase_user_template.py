"""
Couchbase user template (couchbase SDK, lazy import).

Each task entry::

    {"method": "connect", "url": "couchbase://127.0.0.1",
     "user": "Administrator", "password": "password",
     "bucket": "default"}
    {"method": "upsert", "key": "k", "value": {"x": 1}}
    {"method": "get",    "key": "k"}
    {"method": "remove", "key": "k"}
    {"method": "close"}
"""

from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)


def _import_couchbase():
    try:
        from couchbase.auth import PasswordAuthenticator
        from couchbase.cluster import Cluster
        from couchbase.options import ClusterOptions
    except ImportError as error:
        raise RuntimeError(
            "couchbase is required for CouchbaseUser; "
            "install with: pip install couchbase"
        ) from error
    return Cluster, ClusterOptions, PasswordAuthenticator


class CouchbaseUserWrapper(ProtocolUserBase):
    """Locust user driving couchbase SDK calls."""

    _proxy_key = "couchbase_user"
    _request_type = "COUCHBASE"
    host = "couchbase://127.0.0.1"

    def __init__(self, environment):
        super().__init__(environment)
        self._cluster = None
        self._collection = None

    def _connect(self, step: Dict[str, Any]) -> int:
        cluster_cls, options_cls, auth_cls = _import_couchbase()
        self._cluster = cluster_cls(
            step.get("url", self.host),
            options_cls(authenticator=auth_cls(
                step.get("user", "Administrator"),
                step.get("password", ""),
            )),
        )
        bucket = self._cluster.bucket(step.get("bucket", "default"))
        self._collection = bucket.default_collection()
        return 0

    def _upsert(self, step: Dict[str, Any]) -> int:
        if self._collection is None:
            raise RuntimeError("couchbase not connected")
        self._collection.upsert(step["key"], step.get("value", {}))
        return len(str(step.get("value", "")))

    def _get(self, step: Dict[str, Any]) -> int:
        if self._collection is None:
            raise RuntimeError("couchbase not connected")
        result = self._collection.get(step["key"])
        return len(str(result.content_as[dict]))

    def _remove(self, step: Dict[str, Any]) -> int:
        if self._collection is None:
            raise RuntimeError("couchbase not connected")
        self._collection.remove(step["key"])
        return 0

    def _close(self, _: Dict[str, Any]) -> int:
        if self._cluster is not None:
            self._cluster.close()
            self._cluster = None
            self._collection = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "upsert": self._upsert,
            "get": self._get,
            "remove": self._remove,
            "close": self._close,
        }.get(method)


set_wrapper_couchbase_user = make_setter("couchbase_user", CouchbaseUserWrapper)
