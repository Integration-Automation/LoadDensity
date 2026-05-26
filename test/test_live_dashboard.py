import json
import urllib.request
import time

import pytest

from je_load_density.utils.dashboard.live_dashboard import (
    snapshot_metrics,
    start_dashboard,
    stop_dashboard,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance


def _populate(latencies, name="/x"):
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    now = time.time()
    for index, latency in enumerate(latencies):
        test_record_instance.test_record_list.append({
            "Method": "GET", "test_url": name, "name": name,
            "status_code": "200", "response_time_ms": latency,
            "ts": now,
        })


def test_snapshot_metrics_returns_zero_when_empty():
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    snapshot = snapshot_metrics()
    assert snapshot["totals"]["requests"] == 0
    assert snapshot["rps"] == 0.0


def test_snapshot_metrics_computes_rps_and_avg():
    _populate([10.0, 30.0, 50.0])
    snapshot = snapshot_metrics(window_seconds=10.0)
    assert snapshot["totals"]["requests"] == 3
    assert snapshot["rps"] == pytest.approx(0.3, rel=0.01)
    assert snapshot["avg_ms"] == pytest.approx(30.0)


def test_dashboard_serves_html_and_snapshot():
    _populate([5.0, 15.0])
    server = start_dashboard(host="127.0.0.1", port=8763)
    try:
        time.sleep(0.05)
        with urllib.request.urlopen("http://127.0.0.1:8763/", timeout=2) as response:
            html = response.read().decode("utf-8")
        assert "LoadDensity Live" in html

        with urllib.request.urlopen("http://127.0.0.1:8763/snapshot", timeout=2) as response:
            payload = json.loads(response.read())
        assert payload["totals"]["requests"] == 2
        assert payload["avg_ms"] == pytest.approx(10.0)
    finally:
        stop_dashboard()
