"""
Cassandra / ScyllaDB user template (cassandra-driver, lazy import).

Each task entry::

    {"method": "connect", "contact_points": ["127.0.0.1"],
     "port": 9042, "keyspace": "demo"}
    {"method": "execute", "cql": "SELECT * FROM users WHERE id=%s",
     "parameters": [1]}
    {"method": "shutdown"}
"""

import time
from typing import Any, Callable, Dict, List, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_cassandra_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("cassandra_user").configure(user_detail_dict, **kwargs)
    return CassandraUserWrapper


def _import_cassandra():
    try:
        from cassandra.cluster import Cluster
    except ImportError as error:
        raise RuntimeError(
            "cassandra-driver is required for CassandraUser; "
            "install with: pip install cassandra-driver"
        ) from error
    return Cluster


class CassandraUserWrapper(User):
    """Locust user driving cassandra-driver calls."""

    host = "127.0.0.1"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._cluster = None
        self._session = None

    def _connect(self, step: Dict[str, Any]) -> int:
        cluster_cls = _import_cassandra()
        contact_points = step.get("contact_points") or [self.host]
        port = int(step.get("port", 9042))
        self._cluster = cluster_cls(contact_points=contact_points, port=port)
        self._session = self._cluster.connect(step.get("keyspace"))
        return 0

    def _execute(self, step: Dict[str, Any]) -> int:
        if self._session is None:
            raise RuntimeError("cassandra session not open")
        params: Optional[List[Any]] = step.get("parameters")
        rows = self._session.execute(step["cql"], params or None)
        rendered = list(rows)
        return sum(len(str(row)) for row in rendered)

    def _shutdown(self, _: Dict[str, Any]) -> int:
        if self._session is not None:
            self._session.shutdown()
            self._session = None
        if self._cluster is not None:
            self._cluster.shutdown()
            self._cluster = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "execute": self._execute,
            "shutdown": self._shutdown,
        }.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "CASSANDRA", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"cassandra step failed: {error!r}")
            fire_request_event(self.environment, "CASSANDRA", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("cassandra_user")
        if not proxy_user or not proxy_user.tasks:
            return
        tasks = proxy_user.tasks
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks.get("tasks") or []
        if not isinstance(tasks, list):
            return
        for raw_task in tasks:
            if isinstance(raw_task, dict):
                self._do_step(raw_task)
