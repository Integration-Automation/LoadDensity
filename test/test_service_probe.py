import importlib
from pathlib import Path

import pytest


def load_probe(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parent / "smoke"))
    return importlib.import_module("service_probe")


def test_protocol_failure_cannot_be_reported_as_a_passing_service_probe(monkeypatch):
    probe = load_probe(monkeypatch)
    cause = ConnectionError("broker lost")
    with pytest.raises(RuntimeError, match="MQTT publish failed") as raised:
        probe.check_events([{"request_type": "MQTT", "name": "publish", "exception": cause}], 1)
    assert raised.value.__cause__ is cause


def test_missing_protocol_measurement_is_a_probe_failure(monkeypatch):
    probe_module = load_probe(monkeypatch)
    with pytest.raises(RuntimeError, match="Expected 1"):
        probe_module.check_events([], 1)
