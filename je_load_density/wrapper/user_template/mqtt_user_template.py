import secrets
import time
from typing import Any, Dict

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_mqtt_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    """
    設定 MQTT User 的代理使用者
    Configure MQTT User proxy
    """
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])

    locust_wrapper_proxy.user_dict.get("mqtt_user").configure(user_detail_dict, **kwargs)
    return MqttUserWrapper


class MqttUserWrapper(User):
    """
    Locust MQTT User 包裝類別
    Locust MQTT User wrapper class

    Each task entry should look like::

        {
            "method": "publish",        # publish | subscribe | connect | disconnect
            "broker": "127.0.0.1:1883",
            "topic": "telemetry/x",
            "payload": "...",
            "qos": 1,
            "retain": false,
            "username": "...",
            "password": "...",
            "client_id": "...",
            "name": "publish-telemetry"
        }
    """

    host = "127.0.0.1:1883"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None
        self._broker_target = ""

    def _ensure_paho(self):
        try:
            import paho.mqtt.client as paho_client
        except ImportError as error:
            raise RuntimeError("paho-mqtt is required for MqttUser") from error
        return paho_client

    def _ensure_client(self, broker: str, step: Dict[str, Any]):
        paho_client = self._ensure_paho()
        if self._client is not None and self._broker_target == broker:
            return self._client

        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception as error:
                load_density_logger.debug(f"mqtt disconnect before reconnect failed: {error!r}")

        client_id = step.get("client_id") or f"loaddensity-{secrets.token_hex(4)}"
        client = paho_client.Client(client_id=client_id, clean_session=True)
        username = step.get("username")
        password = step.get("password")
        if username:
            client.username_pw_set(username, password or None)

        host, _, port = broker.partition(":")
        client.connect(host, int(port or 1883), keepalive=int(step.get("keepalive", 60)))
        client.loop_start()
        self._client = client
        self._broker_target = broker
        return client

    def _fire(self, name: str, broker: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="MQTT",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=broker,
            response=None,
            start_time=start,
        )

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "publish")).lower()
        broker = step.get("broker") or step.get("host") or self.host
        name = step.get("name") or f"{method}:{step.get('topic', '')}"
        topic = step.get("topic", "")
        qos = int(step.get("qos", 0))
        retain = bool(step.get("retain", False))

        start = time.monotonic()
        try:
            if method == "disconnect":
                if self._client is not None:
                    self._client.loop_stop()
                    self._client.disconnect()
                    self._client = None
                self._fire(name, broker, start, 0)
                return

            client = self._ensure_client(broker, step)

            if method == "connect":
                self._fire(name, broker, start, 0)
                return

            if method == "publish":
                payload = step.get("payload", "")
                info = client.publish(topic, payload=payload, qos=qos, retain=retain)
                if hasattr(info, "wait_for_publish"):
                    info.wait_for_publish(timeout=float(step.get("timeout", 5)))
                length = len(payload) if isinstance(payload, (bytes, str)) else 0
                if info.rc != 0:
                    raise RuntimeError(f"publish failed rc={info.rc}")
                self._fire(name, broker, start, length)
            elif method == "subscribe":
                result, _ = client.subscribe(topic, qos=qos)
                if result != 0:
                    raise RuntimeError(f"subscribe failed rc={result}")
                self._fire(name, broker, start, 0)
            else:
                raise ValueError(f"unsupported mqtt method: {method}")
        except Exception as error:
            self._fire(name, broker, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("mqtt_user")
        if not proxy_user or not proxy_user.tasks:
            return
        tasks = proxy_user.tasks
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks.get("tasks") or []
        if not isinstance(tasks, list):
            load_density_logger.warning("mqtt_user.tasks must be a list")
            return
        for raw_task in tasks:
            if isinstance(raw_task, dict):
                self._do_step(raw_task)

    def on_stop(self) -> None:
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as error:
                load_density_logger.debug(f"mqtt on_stop cleanup failed: {error!r}")
            self._client = None
