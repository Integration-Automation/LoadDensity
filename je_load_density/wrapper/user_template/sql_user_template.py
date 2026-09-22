"""
SQL DB user template.

Each task entry::

    {"method": "execute", "sql": "SELECT 1", "params": {...},
     "name": "smoke", "expect_rows": 1}

Uses SQLAlchemy (soft-dep). The connection_string is passed once via
``start_test(connection_string=...)``.
"""

import time
from typing import Any, Dict, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_sql_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("sql_user").configure(user_detail_dict, **kwargs)
    return SqlUserWrapper


class SqlUserWrapper(User):
    """Locust user that issues SQL queries via SQLAlchemy."""

    host = "sqlite:///:memory:"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._engine = None

    def _ensure_engine(self):
        if self._engine is None:
            try:
                from sqlalchemy import create_engine
            except ImportError as error:
                raise RuntimeError(
                    "SQLAlchemy is required for SqlUser; install with: pip install sqlalchemy"
                ) from error
            proxy_user = locust_wrapper_proxy.user_dict.get("sql_user")
            connection_string = (
                getattr(proxy_user, "connection_string", None)
                or self.host
            )
            self._engine = create_engine(connection_string, future=True)
        return self._engine

    def _fire(self, name: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="SQL",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=name,
            response=None,
            start_time=start,
        )

    def _execute(self, sql: str, params: Optional[Dict[str, Any]]) -> int:
        engine = self._ensure_engine()  # first, so a missing SQLAlchemy gives its clear error
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text(sql), params or {})
            if result.returns_rows:
                rows = result.fetchall()
                return len(rows)
            return result.rowcount or 0

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        sql = step.get("sql")
        if not sql:
            return
        name = step.get("name") or "sql"
        expect_rows = step.get("expect_rows")
        start = time.monotonic()
        try:
            rows = self._execute(sql, step.get("params"))
            if expect_rows is not None and int(rows) != int(expect_rows):
                raise AssertionError(f"expected {expect_rows} rows, got {rows}")
            self._fire(name, start, rows)
        except Exception as error:
            load_density_logger.debug(f"sql step failed: {error!r}")
            self._fire(name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("sql_user")
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
