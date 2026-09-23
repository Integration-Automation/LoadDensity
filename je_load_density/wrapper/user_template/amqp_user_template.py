"""
AMQP / RabbitMQ user template (pika, lazy import).

Each task entry::

    {"method": "connect", "url": "amqp://guest:guest@127.0.0.1:5672/%2F"}
    {"method": "declare_queue", "queue": "q", "durable": false}
    {"method": "publish", "exchange": "", "routing_key": "q", "body": "hello"}
    {"method": "consume", "queue": "q", "auto_ack": true, "max_messages": 1}
    {"method": "close"}

A ``connection`` dict given to the setter supplies default step fields; keys in the step win.
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
from je_load_density.wrapper.user_template._common import (
    fire_request_event,
    with_connection_defaults,
)


def set_wrapper_amqp_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("amqp_user").configure(user_detail_dict, **kwargs)
    return AmqpUserWrapper


def _import_pika():
    try:
        import pika
    except ImportError as error:
        raise RuntimeError(
            "pika is required for AmqpUser; install with: pip install pika"
        ) from error
    return pika


class AmqpUserWrapper(User):
    """Locust user driving pika BlockingConnection calls."""

    host = "amqp://127.0.0.1:5672/%2F"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._connection = None
        self._channel = None

    def _connect(self, step: Dict[str, Any]) -> int:
        pika = _import_pika()
        url = step.get("url", self.host)
        params = pika.URLParameters(url)
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        return 0

    def _declare_queue(self, step: Dict[str, Any]) -> int:
        if self._channel is None:
            raise RuntimeError("amqp channel not open")
        self._channel.queue_declare(
            queue=step.get("queue", ""),
            durable=bool(step.get("durable", False)),
            exclusive=bool(step.get("exclusive", False)),
            auto_delete=bool(step.get("auto_delete", False)),
        )
        return 0

    def _publish(self, step: Dict[str, Any]) -> int:
        if self._channel is None:
            raise RuntimeError("amqp channel not open")
        body = step.get("body", "")
        if isinstance(body, str):
            body = body.encode("utf-8")
        self._channel.basic_publish(
            exchange=step.get("exchange", ""),
            routing_key=step.get("routing_key", ""),
            body=body,
        )
        return len(body)

    def _consume(self, step: Dict[str, Any]) -> int:
        if self._channel is None:
            raise RuntimeError("amqp channel not open")
        max_messages = int(step.get("max_messages", 1))
        auto_ack = bool(step.get("auto_ack", True))
        total = 0
        for _ in range(max_messages):
            method, _props, body = self._channel.basic_get(
                queue=step.get("queue", ""), auto_ack=auto_ack,
            )
            if method is None:
                break
            total += len(body or b"")
        return total

    def _close(self, _: Dict[str, Any]) -> int:
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None
                self._channel = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "declare_queue": self._declare_queue,
            "publish": self._publish,
            "consume": self._consume,
            "close": self._close,
        }.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = with_connection_defaults("amqp_user", parameter_resolver.resolve(raw_task))
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "AMQP", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"amqp step failed: {error!r}")
            fire_request_event(self.environment, "AMQP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("amqp_user")
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
