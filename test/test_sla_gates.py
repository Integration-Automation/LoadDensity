import pytest

from je_load_density.utils.exception.exceptions import LoadDensityAssertException
from je_load_density.utils.sla.sla_gates import assert_sla, evaluate_sla


SUMMARY = {
    "totals": {"requests": 1000, "successes": 990, "failures": 10, "failure_rate": 0.01},
    "latency_overall": {"p50_ms": 50.0, "p90_ms": 110.0, "p95_ms": 180.0,
                        "p99_ms": 320.0, "max_ms": 500.0, "count": 1000},
    "per_name": {
        "/checkout": {"count": 200, "min_ms": 30.0, "max_ms": 400.0,
                      "mean_ms": 80.0, "p50_ms": 70.0, "p90_ms": 150.0,
                      "p95_ms": 220.0, "p99_ms": 380.0},
    },
}


def test_evaluate_sla_passes_overall_p95():
    results = evaluate_sla([{"type": "latency_p95", "value": 200}], summary=SUMMARY)
    assert results[0]["passed"] is True
    assert results[0]["actual"] == pytest.approx(180.0)


def test_evaluate_sla_fails_overall_p95():
    results = evaluate_sla([{"type": "latency_p95", "value": 100}], summary=SUMMARY)
    assert results[0]["passed"] is False
    assert "not lte" in results[0]["reason"]


def test_evaluate_sla_per_name_metric():
    results = evaluate_sla(
        [{"type": "latency_p95", "name": "/checkout", "value": 250}],
        summary=SUMMARY,
    )
    assert results[0]["passed"] is True
    assert results[0]["actual"] == pytest.approx(220.0)


def test_evaluate_sla_supports_failure_rate():
    results = evaluate_sla([{"type": "failure_rate", "value": 0.05}], summary=SUMMARY)
    assert results[0]["passed"] is True


def test_evaluate_sla_supports_min_requests_with_gte():
    results = evaluate_sla(
        [{"type": "requests", "op": "gte", "value": 500}],
        summary=SUMMARY,
    )
    assert results[0]["passed"] is True


def test_evaluate_sla_reports_unknown_metric():
    results = evaluate_sla(
        [{"type": "latency_p95", "name": "/nonexistent", "value": 100}],
        summary=SUMMARY,
    )
    assert results[0]["passed"] is False
    assert "not available" in results[0]["reason"]


def test_evaluate_sla_rejects_unknown_op():
    results = evaluate_sla(
        [{"type": "latency_p95", "op": "approx", "value": 100}],
        summary=SUMMARY,
    )
    assert "unsupported op" in results[0]["reason"]


def test_assert_sla_raises_on_failure():
    with pytest.raises(LoadDensityAssertException):
        assert_sla([{"type": "latency_p95", "value": 100}], summary=SUMMARY)


def test_assert_sla_passes_silently():
    results = assert_sla([{"type": "latency_p95", "value": 1000}], summary=SUMMARY)
    assert results[0]["passed"] is True
