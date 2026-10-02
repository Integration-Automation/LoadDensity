"""Protocol events must provide epoch starts for shared report/dashboard windows."""

import importlib
from types import SimpleNamespace

import pytest

from je_load_density.wrapper.user_template import _common


@pytest.mark.parametrize("module_name,class_name,args", [
    ("async_http", "AsyncHttpUserWrapper", ("health", 42, 3)),
    ("grpc", "GrpcUserWrapper", ("health", "host", 42, 3)),
    ("kafka", "KafkaUserWrapper", ("health", 42, 3)),
    ("mongo", "MongoUserWrapper", ("health", 42, 3)),
    ("mqtt", "MqttUserWrapper", ("health", "host", 42, 3)),
    ("redis", "RedisUserWrapper", ("health", 42, 3)),
    ("socket", "SocketUserWrapper", ("health", "host", "tcp", 42, 3)),
    ("sql", "SqlUserWrapper", ("health", 42, 3)),
    ("sse", "SseUserWrapper", ("health", 42, 3)),
    ("websocket", "WebSocketUserWrapper", ("health", 42, 3)),
])
def test_protocol_events_report_epoch_start_and_monotonic_duration(monkeypatch, module_name, class_name, args):
    module = importlib.import_module(f"je_load_density.wrapper.user_template.{module_name}_user_template")
    clock = SimpleNamespace(time=lambda: 1000, monotonic=lambda: 44)
    monkeypatch.setattr(module, "time", clock)
    monkeypatch.setattr(_common, "time", clock)
    events = []
    environment = SimpleNamespace(events=SimpleNamespace(request=SimpleNamespace(fire=lambda **kw: events.append(kw))))
    getattr(module, class_name)._fire(SimpleNamespace(environment=environment, _url="host"), *args)
    assert events[0]["start_time"] == 998
    assert events[0]["response_time"] == 2000


def test_common_protocol_event_reports_epoch_start(monkeypatch):
    monkeypatch.setattr(_common, "time", SimpleNamespace(time=lambda: 1000, monotonic=lambda: 44))
    events = []
    environment = SimpleNamespace(events=SimpleNamespace(request=SimpleNamespace(fire=lambda **kw: events.append(kw))))
    _common.fire_request_event(environment, "SMTP", "health", 42)
    assert events[0]["start_time"] == 998
    assert events[0]["response_time"] == 2000
