import math

import pytest

from je_load_density.utils.test_record.window_statistics import latency_windows


def test_windows_merge_failed_and_successful_measurements_in_timestamp_order():
    records = [{"start_time": 12.1, "response_time_ms": 90, "error": "HTTP 500"},
               {"start_time": 10.2, "response_time_ms": 10},
               {"start_time": 10.8, "response_time_ms": 30}]
    windows = latency_windows(records, start=10, end=13)
    assert windows == [
        {"start_time": 10.0, "duration_seconds": 1.0, "count": 2, "rps": 2.0,
         "p50_ms": 10.0, "p95_ms": 30.0, "p99_ms": 30.0},
        {"start_time": 11.0, "duration_seconds": 1.0, "count": 0, "rps": 0.0,
         "p50_ms": None, "p95_ms": None, "p99_ms": None},
        {"start_time": 12.0, "duration_seconds": 1.0, "count": 1, "rps": 1.0,
         "p50_ms": 90.0, "p95_ms": 90.0, "p99_ms": 90.0},
    ]


def test_epoch_zero_is_preserved_and_start_time_takes_precedence_over_ts():
    windows = latency_windows([{"start_time": 0, "ts": 50, "response_time_ms": 0}], start=0, end=1)
    assert windows[0]["p50_ms"] == 0
    assert windows[0]["count"] == 1


def test_canonical_records_and_actual_partial_bucket_duration():
    windows = latency_windows([{"started_at": 0.1, "elapsed_ms": 20}, {"started_at": 1.1, "elapsed_ms": 40}],
                              start=0, end=1.5)
    assert [item["rps"] for item in windows] == [1, 2]
    assert windows[1]["duration_seconds"] == 0.5
    assert windows[1]["p99_ms"] == 40


def test_history_is_bounded_without_merging_old_samples_into_percentiles():
    windows = latency_windows([{"ts": value, "response_time_ms": value} for value in range(1000)],
                              start=0, end=1000, max_buckets=3)
    assert [item["start_time"] for item in windows] == [997, 998, 999]
    assert [item["p50_ms"] for item in windows] == [997, 998, 999]


def test_missing_and_invalid_latencies_count_requests_but_leave_a_gap():
    records = [{"ts": 0.1}, {"ts": 0.2, "response_time_ms": math.nan},
               {"ts": 0.3, "response_time_ms": -1}, {"ts": 0.4, "response_time_ms": "bad"}]
    result = latency_windows(records, start=0, end=1)[0]
    assert result["count"] == 4
    assert result["p95_ms"] is None


@pytest.mark.parametrize("kwargs", [{"bucket_size_seconds": 0}, {"max_buckets": 0},
                                    {"start": 2, "end": 1}, {"end": math.inf}])
def test_invalid_windows_fail_before_rendering(kwargs):
    with pytest.raises(ValueError):
        latency_windows([], **kwargs)


def test_empty_input_produces_no_artificial_time_series():
    assert latency_windows([]) == []
