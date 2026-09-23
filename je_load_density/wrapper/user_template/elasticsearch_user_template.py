"""
Elasticsearch / OpenSearch user template (elasticsearch, lazy import).

Each task entry::

    {"method": "connect", "hosts": ["http://127.0.0.1:9200"]}
    {"method": "index", "index": "logs", "document": {"msg": "hi"}}
    {"method": "search", "index": "logs", "body": {"query": {"match_all": {}}}}
    {"method": "get", "index": "logs", "id": "1"}
    {"method": "close"}

A ``connection`` dict given to the setter supplies default step fields; keys in the step win.
"""

import json as json_module
import time
from typing import Any, Callable, Dict, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import (
    fire_request_event,
    with_connection_defaults,
)


def set_wrapper_elasticsearch_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("elasticsearch_user").configure(user_detail_dict, **kwargs)
    return ElasticsearchUserWrapper


def _import_elasticsearch():
    try:
        from elasticsearch import Elasticsearch
    except ImportError as error:
        raise RuntimeError(
            "elasticsearch is required for ElasticsearchUser; "
            "install with: pip install elasticsearch"
        ) from error
    return Elasticsearch


class ElasticsearchUserWrapper(User):
    """Locust user driving elasticsearch-py calls."""

    host = "http://127.0.0.1:9200"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None

    def _connect(self, step: Dict[str, Any]) -> int:
        elasticsearch_cls = _import_elasticsearch()
        hosts = step.get("hosts") or [self.host]
        self._client = elasticsearch_cls(hosts=hosts)
        return 0

    def _index(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("elasticsearch client not connected")
        document = step.get("document", {})
        response = self._client.index(index=step["index"], document=document)
        return len(json_module.dumps(dict(response)))

    def _search(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("elasticsearch client not connected")
        body = step.get("body") or {"query": {"match_all": {}}}
        response = self._client.search(index=step["index"], body=body)
        hits = response.get("hits", {}).get("hits", [])
        return len(json_module.dumps(hits))

    def _get(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("elasticsearch client not connected")
        response = self._client.get(index=step["index"], id=str(step["id"]))
        return len(json_module.dumps(dict(response)))

    def _close(self, _: Dict[str, Any]) -> int:
        if self._client is not None:
            self._client.close()
            self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "index": self._index,
            "search": self._search,
            "get": self._get,
            "close": self._close,
        }.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = with_connection_defaults("elasticsearch_user", parameter_resolver.resolve(raw_task))
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "ES", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"elasticsearch step failed: {error!r}")
            fire_request_event(self.environment, "ES", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("elasticsearch_user")
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
