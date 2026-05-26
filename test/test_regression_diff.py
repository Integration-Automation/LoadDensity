import pytest

from je_load_density.utils.regression.diff import diff_runs, summarise_records
from je_load_density.utils.test_record.sqlite_persistence import persist_records
from je_load_density.utils.test_record.test_record_class import test_record_instance


def _populate_records(latencies, name="/checkout"):
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    for latency in latencies:
        test_record_instance.test_record_list.append({
            "Method": "GET", "test_url": name, "name": name,
            "status_code": "200", "response_time_ms": latency,
            "response_length": 100, "error": None,
        })


def test_summarise_records_computes_percentiles():
    records = [
        {"name": "/x", "outcome": "success", "response_time_ms": 10.0},
        {"name": "/x", "outcome": "success", "response_time_ms": 20.0},
        {"name": "/x", "outcome": "failure", "response_time_ms": 30.0},
    ]
    summary = summarise_records(records)
    assert summary["/x"]["count"] == 3
    assert summary["/x"]["failures"] == 1
    assert summary["/x"]["failure_rate"] == pytest.approx(1 / 3)
    assert summary["/x"]["p50_ms"] == pytest.approx(20.0)


def test_summarise_handles_empty():
    assert summarise_records([]) == {}


def test_diff_runs_flags_regression(tmp_path):
    database = str(tmp_path / "runs.db")

    _populate_records([100.0] * 10)
    baseline_id = persist_records(database, label="baseline")

    _populate_records([300.0] * 10)
    current_id = persist_records(database, label="current")

    result = diff_runs(database, baseline_id, current_id, tolerance=0.10)
    assert result["has_regressions"] is True
    assert any(reg["name"] == "/checkout" for reg in result["regressions"])
    deltas = result["per_name"]["/checkout"]["deltas"]
    assert deltas["p95_ms"]["pct"] > 0.10


def test_diff_runs_no_regression_when_within_tolerance(tmp_path):
    database = str(tmp_path / "runs.db")

    _populate_records([100.0] * 10)
    baseline_id = persist_records(database, label="baseline")

    _populate_records([105.0] * 10)
    current_id = persist_records(database, label="current")

    result = diff_runs(database, baseline_id, current_id, tolerance=0.10)
    assert result["has_regressions"] is False
