"""Exercise installed LoadDensity adapters against healthy Compose services."""

import os
import threading
from types import SimpleNamespace

import je_load_density  # noqa: F401 - patch before client networking imports.


def check_events(events: list[dict], expected: int) -> None:
    if len(events) != expected:
        raise RuntimeError(f"Expected {expected} measured requests, got {len(events)}")
    for event in events:
        if event["exception"] is not None:
            raise RuntimeError(f"{event['request_type']} {event['name']} failed") from event["exception"]
        if event["response_time"] < 0 or event["response_length"] < 0:
            raise RuntimeError("Invalid protocol measurement")


def environment():
    events = []
    return SimpleNamespace(events=SimpleNamespace(request=SimpleNamespace(fire=lambda **kw: events.append(kw)))), events


def redis() -> None:
    from je_load_density.wrapper.user_template.redis_user_template import RedisUserWrapper

    env, events = environment()
    user = RedisUserWrapper(env)
    user.host = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:6379/0?socket_timeout=3&socket_connect_timeout=3"
    try:
        for step in [{"method": "set", "key": "smoke", "value": "capacity"},
                     {"method": "get", "key": "smoke", "expect": "capacity"},
                     {"method": "delete", "key": "smoke"}]:
            user._do_step(step)
        check_events(events, 3)
        if events[1]["response_length"] != 8:
            raise RuntimeError("Redis adapter did not measure returned bytes")
    finally:
        if user._client is not None:
            user._client.close()


def mqtt() -> None:
    from paho.mqtt.client import CallbackAPIVersion, Client

    from je_load_density.wrapper.user_template.mqtt_user_template import MqttUserWrapper

    broker = os.environ.get("MQTT_HOST", "mosquitto")
    received = threading.Event()
    subscriber = Client(CallbackAPIVersion.VERSION2)
    subscriber.on_message = lambda _client, _data, message: received.set() if message.payload == b"capacity" else None
    subscriber.connect(broker, 1883)
    subscriber.subscribe("smoke/adapter", qos=1)
    subscriber.loop_start()
    env, events = environment()
    user = MqttUserWrapper(env)
    try:
        user._do_step({"method": "publish", "broker": broker, "topic": "smoke/adapter",
                       "payload": "capacity", "qos": 1, "retain": True, "timeout": 5})
        check_events(events, 1)
        if not received.wait(5):
            raise RuntimeError("MQTT publish was not delivered to the subscriber")
    finally:
        user.on_stop()
        subscriber.disconnect()
        subscriber.loop_stop()


def sql() -> None:
    from je_load_density.wrapper.user_template.sql_user_template import SqlUserWrapper

    env, events = environment()
    user = SqlUserWrapper(env)
    try:
        user._do_step({"sql": "SELECT 1", "expect_rows": 1})
        check_events(events, 1)
    finally:
        if user._engine is not None:
            user._engine.dispose()


if __name__ == "__main__":
    for probe in (redis, mqtt, sql):
        probe()
        print(f"service adapter passed: {probe.__name__}")
