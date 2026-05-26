import time

import pytest

from je_load_density.utils.reliability.adaptive_retry import (
    AdaptiveRetryPolicy,
    classify_error,
    run_with_retry,
)
from je_load_density.utils.reliability.failure_budget import FailureBudget
from je_load_density.utils.reliability.network_conditioner import NetworkConditioner
from je_load_density.utils.reliability.process_supervisor import with_watchdog


# ---------------------------------------------------------------- retry
def test_classify_error_buckets_transient_and_flaky_and_permanent():
    assert classify_error(ConnectionError("x")) == "transient"
    assert classify_error(TimeoutError("x")) == "transient"
    assert classify_error(AssertionError("x")) == "flaky"
    assert classify_error(ValueError("x")) == "permanent"


def test_run_with_retry_returns_after_transient_recovery():
    attempts = []

    def fn():
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError("flap")
        return "ok"

    result = run_with_retry(fn, policy=AdaptiveRetryPolicy(transient_budget=5,
                                                            base_delay=0,
                                                            jitter=0),
                            sleeper=lambda _: None)
    assert result == "ok"
    assert len(attempts) == 3


def test_run_with_retry_exhausts_budget_then_raises():
    def fn():
        raise ConnectionError("dead")

    policy = AdaptiveRetryPolicy(transient_budget=2, base_delay=0, jitter=0)
    with pytest.raises(ConnectionError):
        run_with_retry(fn, policy=policy, sleeper=lambda _: None)


def test_run_with_retry_does_not_retry_permanent_errors():
    attempts = []

    def fn():
        attempts.append(1)
        raise ValueError("permanent")

    policy = AdaptiveRetryPolicy(base_delay=0, jitter=0)
    with pytest.raises(ValueError):
        run_with_retry(fn, policy=policy, sleeper=lambda _: None)
    assert len(attempts) == 1


def test_retry_policy_backoff_grows_then_caps():
    policy = AdaptiveRetryPolicy(base_delay=0.1, backoff_factor=2.0,
                                  max_delay=0.3, jitter=0)
    delays = [policy._next_delay(attempt) for attempt in range(1, 6)]
    assert delays[0] == pytest.approx(0.1)
    assert delays[1] == pytest.approx(0.2)
    assert all(delay <= 0.3 + 1e-9 for delay in delays)


# ---------------------------------------------------------------- budget
def test_failure_budget_records_and_evicts():
    budget = FailureBudget(threshold=0.5, window_seconds=10.0, min_samples=2)
    budget.record(failed=False, now=0)
    budget.record(failed=True, now=1)
    assert budget.sample_count() == 2
    assert budget.failure_rate(now=1) == pytest.approx(0.5)

    budget.record(failed=False, now=100)
    # earlier samples evicted
    assert budget.sample_count() == 1


def test_failure_budget_is_breached_above_threshold_with_enough_samples():
    budget = FailureBudget(threshold=0.5, window_seconds=10.0, min_samples=3)
    budget.record(failed=True, now=0)
    budget.record(failed=True, now=0)
    assert budget.is_breached(now=0) is False  # not enough samples yet
    budget.record(failed=True, now=0)
    assert budget.is_breached(now=0) is True


# ---------------------------------------------------------------- conditioner
def test_network_conditioner_sleeps_for_latency():
    conditioner = NetworkConditioner(latency_ms=50, jitter_ms=0)
    sleeps = []
    conditioner.apply({}, sleeper=lambda s: sleeps.append(s))
    assert sleeps == [0.05]


def test_network_conditioner_raises_on_full_loss():
    conditioner = NetworkConditioner(loss_rate=1.0)
    with pytest.raises(ConnectionError):
        conditioner.apply({}, sleeper=lambda _: None)


def test_network_conditioner_name_filter_skips_other_tasks():
    conditioner = NetworkConditioner(latency_ms=100, name_filter="/checkout")
    sleeps = []
    conditioner.apply({"name": "/home"}, sleeper=lambda s: sleeps.append(s))
    assert sleeps == []


def test_network_conditioner_applies_to_matching_name():
    conditioner = NetworkConditioner(latency_ms=20, jitter_ms=0,
                                       name_filter="/checkout")
    sleeps = []
    conditioner.apply({"name": "/checkout"}, sleeper=lambda s: sleeps.append(s))
    assert sleeps == [0.02]


# ---------------------------------------------------------------- watchdog
def test_with_watchdog_returns_value_on_success():
    assert with_watchdog(lambda x: x * 2, 5, timeout_seconds=1) == 10


def test_with_watchdog_raises_timeout_on_hang():
    def slow():
        time.sleep(0.5)

    with pytest.raises(TimeoutError):
        with_watchdog(slow, timeout_seconds=0.05)


def test_with_watchdog_propagates_exception():
    def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        with_watchdog(boom, timeout_seconds=1)
