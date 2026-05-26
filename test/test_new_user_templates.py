from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template.kafka_user_template import (
    set_wrapper_kafka_user,
)
from je_load_density.wrapper.user_template.redis_user_template import (
    set_wrapper_redis_user,
)
from je_load_density.wrapper.user_template.sql_user_template import (
    set_wrapper_sql_user,
)
from je_load_density.wrapper.user_template.sse_user_template import (
    _parse_sse_lines,
    set_wrapper_sse_user,
)


def test_sse_parse_lines_builds_events():
    raw = iter([
        "event: ready",
        "data: hello",
        "",
        "data: world",
        "",
    ])
    events = list(_parse_sse_lines(raw))
    assert events[0] == {"event": "ready", "data": "hello"}
    assert events[1] == {"data": "world"}


def test_set_wrapper_sse_user_configures_proxy():
    cls = set_wrapper_sse_user(
        {"user": "sse_user"},
        tasks=[{"method": "open", "request_url": "https://api/stream"}],
    )
    assert cls.__name__ == "SseUserWrapper"
    proxy = locust_wrapper_proxy.user_dict["sse_user"]
    assert proxy.tasks[0]["method"] == "open"


def test_set_wrapper_sql_user_carries_connection_string():
    cls = set_wrapper_sql_user(
        {"user": "sql_user"},
        connection_string="sqlite:///:memory:",
        tasks=[{"method": "execute", "sql": "SELECT 1"}],
    )
    proxy = locust_wrapper_proxy.user_dict["sql_user"]
    assert cls.__name__ == "SqlUserWrapper"
    assert proxy.connection_string == "sqlite:///:memory:"


def test_set_wrapper_redis_user_carries_connection():
    cls = set_wrapper_redis_user(
        {"user": "redis_user"},
        connection={"url": "redis://localhost:6379/1"},
        tasks=[{"method": "set", "key": "k", "value": "v"}],
    )
    proxy = locust_wrapper_proxy.user_dict["redis_user"]
    assert cls.__name__ == "RedisUserWrapper"
    assert proxy.connection["url"] == "redis://localhost:6379/1"


def test_set_wrapper_kafka_user_carries_bootstrap():
    cls = set_wrapper_kafka_user(
        {"user": "kafka_user"},
        bootstrap_servers=["broker:9092"],
        tasks=[{"method": "produce", "topic": "events", "value": "x"}],
    )
    proxy = locust_wrapper_proxy.user_dict["kafka_user"]
    assert cls.__name__ == "KafkaUserWrapper"
    assert proxy.bootstrap_servers == ["broker:9092"]


def test_proxy_registry_contains_all_new_templates():
    keys = set(locust_wrapper_proxy.user_dict)
    assert {"sse_user", "sql_user", "redis_user", "kafka_user"} <= keys
