"""
Kafka user template.

Each task entry::

    {"method": "produce", "topic": "events", "value": "hello",
     "key": "session-1", "name": "publish"}
    {"method": "consume", "topic": "events", "timeout": 5,
     "expect": "hello"}
    {"method": "flush"}
"""

import json
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


def set_wrapper_kafka_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("kafka_user").configure(user_detail_dict, **kwargs)
    return KafkaUserWrapper


def _encode(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value).encode("utf-8")


class KafkaUserWrapper(User):
    """Locust user that produces/consumes against a Kafka cluster."""

    host = "localhost:9092"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._producer = None
        self._consumers: Dict[str, Any] = {}

    def _bootstrap_servers(self):
        proxy_user = locust_wrapper_proxy.user_dict.get("kafka_user")
        servers = getattr(proxy_user, "bootstrap_servers", None)
        return servers if servers else [self.host]

    def _ensure_producer(self):
        if self._producer is None:
            try:
                from kafka import KafkaProducer
            except ImportError as error:
                raise RuntimeError(
                    "kafka-python is required for KafkaUser; install with: pip install kafka-python"
                ) from error
            self._producer = KafkaProducer(bootstrap_servers=self._bootstrap_servers())
        return self._producer

    def _ensure_consumer(self, topic: str, timeout: float):
        existing = self._consumers.get(topic)
        if existing is not None:
            return existing
        try:
            from kafka import KafkaConsumer
        except ImportError as error:
            raise RuntimeError(
                "kafka-python is required for KafkaUser; install with: pip install kafka-python"
            ) from error
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self._bootstrap_servers(),
            consumer_timeout_ms=int(timeout * 1000),
            auto_offset_reset="latest",
            enable_auto_commit=False,
        )
        self._consumers[topic] = consumer
        return consumer

    def _fire(self, name: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="KAFKA",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=name,
            response=None,
            start_time=start,
        )

    def _do_produce(self, step: Dict[str, Any]) -> int:
        producer = self._ensure_producer()
        value = _encode(step.get("value", b""))
        key = step.get("key")
        future = producer.send(
            step["topic"],
            value=value,
            key=_encode(key) if key is not None else None,
        )
        future.get(timeout=float(step.get("timeout", 5)))
        return len(value)

    def _do_consume(self, step: Dict[str, Any]) -> int:
        consumer = self._ensure_consumer(step["topic"], float(step.get("timeout", 5)))
        expect = step.get("expect")
        for record in consumer:
            payload = record.value or b""
            text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else str(payload)
            if expect is None or str(expect) in text:
                return len(payload)
        raise TimeoutError(f"kafka consume {step['topic']} timed out without match")

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        start = time.monotonic()
        try:
            length = self._dispatch(method, step)
            self._fire(name, start, length)
        except Exception as error:
            load_density_logger.debug(f"kafka step failed: {error!r}")
            self._fire(name, start, 0, error)

    def _dispatch(self, method: str, step: Dict[str, Any]) -> int:
        if method == "produce":
            return self._do_produce(step)
        if method == "consume":
            return self._do_consume(step)
        if method == "flush":
            if self._producer is not None:
                self._producer.flush(float(step.get("timeout", 5)))
            return 0
        if method == "close":
            if self._producer is not None:
                self._producer.close()
                self._producer = None
            for consumer in self._consumers.values():
                consumer.close()
            self._consumers.clear()
            return 0
        raise ValueError(f"unsupported kafka method: {method}")

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("kafka_user")
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
