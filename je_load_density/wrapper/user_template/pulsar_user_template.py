"""
Pulsar user template (pulsar-client, lazy import).

Each task entry::

    {"method": "connect", "url": "pulsar://127.0.0.1:6650"}
    {"method": "produce", "topic": "t", "payload": "hello"}
    {"method": "consume", "topic": "t", "subscription": "s",
     "max_messages": 1, "timeout_ms": 1000}
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


def set_wrapper_pulsar_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("pulsar_user").configure(user_detail_dict, **kwargs)
    return PulsarUserWrapper


def _import_pulsar():
    try:
        import pulsar
    except ImportError as error:
        raise RuntimeError(
            "pulsar-client is required for PulsarUser; "
            "install with: pip install pulsar-client"
        ) from error
    return pulsar


def _payload_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("utf-8")


class PulsarUserWrapper(User):
    """Locust user driving pulsar-client calls."""

    host = "pulsar://127.0.0.1:6650"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None
        self._producers: Dict[str, Any] = {}
        self._consumers: Dict[str, Any] = {}

    def _connect(self, step: Dict[str, Any]) -> int:
        pulsar = _import_pulsar()
        self._client = pulsar.Client(step.get("url", self.host))
        return 0

    def _producer_for(self, topic: str):
        producer = self._producers.get(topic)
        if producer is None:
            producer = self._client.create_producer(topic)
            self._producers[topic] = producer
        return producer

    def _consumer_for(self, topic: str, subscription: str):
        key = f"{topic}::{subscription}"
        consumer = self._consumers.get(key)
        if consumer is None:
            consumer = self._client.subscribe(topic, subscription)
            self._consumers[key] = consumer
        return consumer

    def _produce(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("pulsar client not connected")
        payload = _payload_bytes(step.get("payload", ""))
        self._producer_for(step["topic"]).send(payload)
        return len(payload)

    def _consume(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("pulsar client not connected")
        consumer = self._consumer_for(step["topic"], step.get("subscription", "default"))
        timeout = int(step.get("timeout_ms", 1000))
        total = 0
        for _ in range(int(step.get("max_messages", 1))):
            message = consumer.receive(timeout_millis=timeout)
            total += len(message.data())
            consumer.acknowledge(message)
        return total

    def _close(self, _: Dict[str, Any]) -> int:
        for producer in self._producers.values():
            producer.close()
        self._producers.clear()
        for consumer in self._consumers.values():
            consumer.close()
        self._consumers.clear()
        if self._client is not None:
            self._client.close()
            self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "produce": self._produce,
            "consume": self._consume,
            "close": self._close,
        }.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = with_connection_defaults("pulsar_user", parameter_resolver.resolve(raw_task))
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "PULSAR", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"pulsar step failed: {error!r}")
            fire_request_event(self.environment, "PULSAR", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("pulsar_user")
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
