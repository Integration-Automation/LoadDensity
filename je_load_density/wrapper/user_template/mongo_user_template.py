"""
MongoDB user template.

Each task::

    {"method": "find_one",  "database": "shop", "collection": "users",
     "filter": {"email": "u@x"}, "name": "lookup"}
    {"method": "insert_one", "database": "shop", "collection": "events",
     "document": {"k": "v"}}
    {"method": "update_one", "database": "shop", "collection": "events",
     "filter": {"_id": 1}, "update": {"$set": {"v": 2}}}
    {"method": "count", "database": "shop", "collection": "events",
     "filter": {}, "expect_min": 1}

Requires the ``pymongo`` soft-dependency.
"""

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


def set_wrapper_mongo_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("mongo_user").configure(user_detail_dict, **kwargs)
    return MongoUserWrapper


class MongoUserWrapper(User):
    """Locust user that exercises a MongoDB instance via pymongo."""

    host = "mongodb://127.0.0.1:27017"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                from pymongo import MongoClient
            except ImportError as error:
                raise RuntimeError(
                    "pymongo is required for MongoUser; install with: pip install pymongo"
                ) from error
            proxy_user = locust_wrapper_proxy.user_dict.get("mongo_user")
            conn = (getattr(proxy_user, "connection", None) or {})
            uri = conn.get("uri") or self.host
            self._client = MongoClient(uri,
                                        serverSelectionTimeoutMS=int(conn.get("timeout_ms", 5000)))
        return self._client

    def _collection(self, step: Dict[str, Any]):
        client = self._ensure_client()
        database = step.get("database") or "test"
        collection = step.get("collection") or "default"
        return client[database][collection]

    def _fire(self, name: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="MONGO",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=name,
            response=None,
            start_time=start,
        )

    def _coerce(self, value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, list):
            return len(value)
        if isinstance(value, int):
            return value
        return 1

    def _handler_for(self, method: str) -> Optional[Callable[..., Any]]:
        return {
            "find_one":   lambda step: self._collection(step).find_one(step.get("filter") or {}),
            "find":       lambda step: list(self._collection(step).find(step.get("filter") or {})
                                              .limit(int(step.get("limit", 0)))),
            "insert_one": lambda step: self._collection(step).insert_one(step.get("document") or {}),
            "update_one": lambda step: self._collection(step)
                                              .update_one(step.get("filter") or {},
                                                          step.get("update") or {}),
            "delete_one": lambda step: self._collection(step).delete_one(step.get("filter") or {}),
            "count":      lambda step: self._collection(step)
                                              .count_documents(step.get("filter") or {}),
        }.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._handler_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            result = handler(step)
            expect_min = step.get("expect_min")
            if expect_min is not None and self._coerce(result) < int(expect_min):
                raise AssertionError(f"mongo {method} expected >= {expect_min} rows")
            self._fire(name, start, self._coerce(result))
        except Exception as error:
            load_density_logger.debug(f"mongo step failed: {error!r}")
            self._fire(name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("mongo_user")
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
