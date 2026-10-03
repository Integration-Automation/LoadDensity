import json
import time
import urllib.request

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
    assert snapshot["rps"] == pytest.approx(0.0)


def test_snapshot_metrics_computes_rps_and_avg():
    _populate([10.0, 30.0, 50.0])
    snapshot = snapshot_metrics(window_seconds=10.0)
    assert snapshot["totals"]["requests"] == 3
    assert snapshot["rps"] == pytest.approx(0.3, rel=0.01)
    assert snapshot["avg_ms"] == pytest.approx(30.0)


def test_dashboard_serves_html_and_snapshot():
    _populate([5.0, 15.0])
    start_dashboard(host="127.0.0.1", port=8763)
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


def test_dashboard_windows_and_rate_include_failures_and_use_request_start(monkeypatch):
    from je_load_density.utils.dashboard import live_dashboard

    monkeypatch.setattr(live_dashboard.time, "time", lambda: 100.0)
    test_record_instance.clear_records()
    test_record_instance.test_record_list.append({"start_time": 90.2, "response_time_ms": 10})
    test_record_instance.error_record_list.append({"start_time": 99.2, "response_time_ms": 50, "error": "500"})
    snapshot = snapshot_metrics()
    assert snapshot["rps"] == pytest.approx(0.2)
    assert snapshot["avg_ms"] == 30
    assert len(snapshot["latency_windows"]) == 120
    assert snapshot["latency_windows"][-1]["p95_ms"] == 50
    assert snapshot["latency_windows"][-2]["p50_ms"] is None


def test_sse_client_does_not_block_snapshot_or_shutdown():
    _populate([5])
    server = start_dashboard(port=0, refresh_seconds=0.05)
    root = f"http://127.0.0.1:{server._httpd.server_port}"
    stream = urllib.request.urlopen(root + "/events", timeout=2)
    try:
        assert stream.readline().startswith(b"data: ")
        with urllib.request.urlopen(root + "/snapshot", timeout=2) as response:
            assert json.loads(response.read())["totals"]["requests"] == 1
        thread = server._thread
        before = time.monotonic()
        stop_dashboard()
        assert time.monotonic() - before < 1.5
        assert not thread.is_alive()
    finally:
        stream.close()
        stop_dashboard()


def test_invalid_latency_keeps_request_counts_and_json_finite():
    _populate([10, float("nan"), float("inf"), -2, "unknown", True])
    snapshot = snapshot_metrics()
    assert snapshot["totals"]["requests"] == 6
    assert snapshot["latency_overall"]["count"] == 1
    assert snapshot["latency_overall"]["p95_ms"] == 10
    assert snapshot["per_name"]["/x"]["count"] == 1
    assert snapshot["rps"] == pytest.approx(0.6)
    json.dumps(snapshot, allow_nan=False)


def test_large_finite_latencies_keep_finite_mean_and_request_counts():
    _populate([1e308, 1e308])
    snapshot = snapshot_metrics()
    assert snapshot["totals"]["requests"] == 2
    assert snapshot["avg_ms"] == 1e308
    assert snapshot["per_name"]["/x"]["mean_ms"] == 1e308
    json.dumps(snapshot, allow_nan=False)
