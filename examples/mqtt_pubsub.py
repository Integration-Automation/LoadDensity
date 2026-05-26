"""
MQTT pub/sub recipe against the local broker in docker/docker-compose.yml.

Requires: ``pip install "je_load_density[mqtt]"`` and a broker on
127.0.0.1:1883 (``docker compose -f docker/docker-compose.yml up -d mosquitto``).
"""

from je_load_density import start_test


def main() -> None:
    start_test(
        user_detail_dict={"user": "mqtt_user"},
        user_count=10, spawn_rate=5, test_time=30,
        tasks=[
            {"method": "connect",   "broker": "127.0.0.1:1883"},
            {"method": "subscribe", "topic": "telemetry/in", "qos": 1},
            {"method": "publish",   "topic": "telemetry/out",
             "payload": "ping ${uuid()}", "qos": 1},
            {"method": "disconnect"},
        ],
    )


if __name__ == "__main__":
    main()
