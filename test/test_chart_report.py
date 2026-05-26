import pytest

from je_load_density.utils.generate_report.generate_chart_report import (
    ChartDependencyError,
    _bucket_rps,
    _collect_points,
    generate_chart_report,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance


def _push_records(latencies):
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    for i, latency in enumerate(latencies):
        test_record_instance.test_record_list.append({
            "Method": "GET", "test_url": "/x", "name": "/x",
            "status_code": "200", "response_time_ms": latency,
            "ts": float(i),
        })


def test_collect_points_skips_records_without_latency():
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    test_record_instance.test_record_list.append({"Method": "GET"})
    test_record_instance.test_record_list.append({"response_time_ms": 12.0, "ts": 1.0})
    timestamps, latencies = _collect_points()
    assert latencies == [12.0]
    assert timestamps == [1.0]


def test_bucket_rps_returns_counts_per_bucket():
    xs, counts = _bucket_rps([0.0, 0.5, 1.5, 2.1], bucket_size=1.0)
    assert counts == [2, 1, 1]
    assert xs[0] == pytest.approx(0.0)
    assert xs[1] == pytest.approx(1.0)


def test_bucket_rps_empty():
    assert _bucket_rps([]) == ([], [])


def test_generate_chart_report_writes_png(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    monkeypatch.chdir(tmp_path)
    _push_records([10.0, 20.0, 30.0])
    out = generate_chart_report("charts")
    assert out["latency"].endswith("charts-latency.png")
    assert out["rps"].endswith("charts-rps.png")


def test_generate_chart_report_raises_when_no_records(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    monkeypatch.chdir(tmp_path)
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    with pytest.raises(ChartDependencyError):
        generate_chart_report("charts")
