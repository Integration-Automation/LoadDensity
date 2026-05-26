import pytest

from je_load_density.utils.load_shapes.shapes import (
    _soak_tick,
    _spike_tick,
    _stages_tick,
    build_load_shape,
)


def test_stages_tick_picks_correct_stage():
    stages = [
        {"duration": 10, "users": 5,  "spawn_rate": 1},
        {"duration": 20, "users": 25, "spawn_rate": 5},
    ]
    assert _stages_tick(stages, 1) == (5, 1)
    assert _stages_tick(stages, 12) == (25, 5)
    assert _stages_tick(stages, 31) is None


def test_spike_tick_baseline_then_spike_then_baseline_then_done():
    config = {
        "baseline_users": 10, "spike_users": 100, "spawn_rate": 20,
        "pre_seconds": 10, "spike_seconds": 5, "post_seconds": 10,
    }
    assert _spike_tick(config, 1) == (10, 20)
    assert _spike_tick(config, 12) == (100, 20)
    assert _spike_tick(config, 20) == (10, 20)
    assert _spike_tick(config, 30) is None


def test_soak_tick_ramps_then_holds_then_cools():
    config = {"users": 100, "spawn_rate": 10,
              "ramp_seconds": 10, "hold_seconds": 20, "cooldown_seconds": 10}
    users_at_5s, _ = _soak_tick(config, 5)
    assert 40 <= users_at_5s <= 60
    users_at_15s, _ = _soak_tick(config, 15)
    assert users_at_15s == 100
    users_at_35s, _ = _soak_tick(config, 35)
    assert users_at_35s < 100
    assert _soak_tick(config, 1000) is None


def test_build_load_shape_unknown_raises():
    with pytest.raises(ValueError):
        build_load_shape("unknown", {})


def test_build_load_shape_returns_locust_subclass():
    pytest.importorskip("locust")
    shape_cls = build_load_shape("stages", {"stages": [
        {"duration": 5, "users": 1, "spawn_rate": 1},
    ]})
    instance = shape_cls()
    assert hasattr(instance, "tick")


def test_build_load_shape_spike_and_soak():
    pytest.importorskip("locust")
    spike_cls = build_load_shape("spike", {"baseline_users": 1, "spike_users": 5})
    soak_cls = build_load_shape("soak", {"users": 10})
    assert spike_cls.__name__ == "SpikeShape"
    assert soak_cls.__name__ == "SoakShape"
