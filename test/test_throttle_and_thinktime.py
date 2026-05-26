import time

import pytest

from je_load_density.utils.throttle.rps_throttle import (
    RpsThrottle,
    get_throttle,
    reset_throttles,
)
from je_load_density.wrapper.user_template.scenario_runner import (
    _apply_think_time,
    _think_time_seconds,
)


def test_rps_throttle_rejects_nonpositive():
    with pytest.raises(ValueError):
        RpsThrottle(rps=0)


def test_rps_throttle_first_burst_is_immediate():
    reset_throttles()
    throttle = RpsThrottle(rps=10.0, burst=3)
    start = time.monotonic()
    for _ in range(3):
        throttle.acquire()
    assert time.monotonic() - start < 0.05


def test_rps_throttle_blocks_after_burst():
    reset_throttles()
    throttle = RpsThrottle(rps=20.0, burst=1)
    throttle.acquire()
    start = time.monotonic()
    throttle.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.04


def test_get_throttle_returns_shared_instance():
    reset_throttles()
    a = get_throttle("key", rps=5)
    b = get_throttle("key", rps=999)
    assert a is b


def test_think_time_seconds_fixed_and_range():
    assert _think_time_seconds(0.5) == pytest.approx(0.5)
    assert _think_time_seconds(0) == 0
    assert _think_time_seconds(None) == 0
    spread = _think_time_seconds({"min": 0.1, "max": 0.2})
    assert 0.1 <= spread < 0.2


def test_apply_think_time_sleeps_when_set():
    start = time.monotonic()
    _apply_think_time({"think_time": 0.05})
    assert time.monotonic() - start >= 0.04


def test_apply_think_time_noop_when_missing():
    start = time.monotonic()
    _apply_think_time({})
    assert time.monotonic() - start < 0.01
