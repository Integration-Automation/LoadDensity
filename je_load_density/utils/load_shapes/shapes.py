"""
LoadTestShape factories.

Three reusable shapes that subclass ``locust.LoadTestShape`` and
schedule ``(user_count, spawn_rate)`` per second:

* :class:`StagesShape` — list of dict stages
  ``{"duration": s, "users": N, "spawn_rate": R}``.
* :class:`SpikeShape` — baseline → spike → baseline.
* :class:`SoakShape` — ramp up, hold, ramp down.

``locust`` is imported lazily so the shapes can be exercised in unit
tests without spinning up an environment.
"""

from typing import Any, Dict, List, Optional, Tuple


def _require_load_test_shape():
    try:
        from locust import LoadTestShape
    except ImportError as error:
        raise RuntimeError(
            "locust is required to use LoadTestShape; install with: pip install locust"
        ) from error
    return LoadTestShape


def _stages_tick(stages: List[Dict[str, Any]], run_time: float) -> Optional[Tuple[int, int]]:
    cumulative = 0.0
    for stage in stages:
        cumulative += float(stage.get("duration", 0))
        if run_time < cumulative:
            return int(stage.get("users", 0)), int(stage.get("spawn_rate", 1))
    return None


def _spike_tick(config: Dict[str, Any], run_time: float) -> Optional[Tuple[int, int]]:
    baseline = int(config.get("baseline_users", 0))
    spike = int(config.get("spike_users", baseline))
    spawn_rate = int(config.get("spawn_rate", 10))
    pre = float(config.get("pre_seconds", 30))
    hold = float(config.get("spike_seconds", 30))
    post = float(config.get("post_seconds", 30))

    if run_time < pre:
        return baseline, spawn_rate
    if run_time < pre + hold:
        return spike, spawn_rate
    if run_time < pre + hold + post:
        return baseline, spawn_rate
    return None


def _soak_tick(config: Dict[str, Any], run_time: float) -> Optional[Tuple[int, int]]:
    users = int(config.get("users", 0))
    spawn_rate = int(config.get("spawn_rate", max(1, users // 10)))
    ramp = float(config.get("ramp_seconds", 60))
    hold = float(config.get("hold_seconds", 600))
    cool = float(config.get("cooldown_seconds", 60))

    if run_time < ramp and ramp > 0:
        fraction = run_time / ramp
        return max(1, int(users * fraction)), spawn_rate
    if run_time < ramp + hold:
        return users, spawn_rate
    if run_time < ramp + hold + cool and cool > 0:
        fraction = 1 - ((run_time - ramp - hold) / cool)
        return max(0, int(users * fraction)), spawn_rate
    return None


def _make_shape_class(name: str, tick_func):
    base = _require_load_test_shape()

    class _Shape(base):
        config: Dict[str, Any] = {}

        def tick(self) -> Optional[Tuple[int, int]]:
            return tick_func(self.config, self.get_run_time())

    _Shape.__name__ = name
    return _Shape


def StagesShape(stages: List[Dict[str, Any]]):
    cls = _make_shape_class("StagesShape", lambda cfg, t: _stages_tick(cfg["stages"], t))
    cls.config = {"stages": list(stages)}
    return cls


def SpikeShape(**config):
    cls = _make_shape_class("SpikeShape", _spike_tick)
    cls.config = dict(config)
    return cls


def SoakShape(**config):
    cls = _make_shape_class("SoakShape", _soak_tick)
    cls.config = dict(config)
    return cls


_SHAPE_FACTORIES = {
    "stages": lambda cfg: StagesShape(cfg.get("stages", [])),
    "spike": lambda cfg: SpikeShape(**cfg),
    "soak": lambda cfg: SoakShape(**cfg),
}


def build_load_shape(name: str, config: Optional[Dict[str, Any]] = None):
    """
    Construct one of the built-in shapes by name. Returns the Locust
    LoadTestShape subclass, ready to pass to ``Environment(shape_class=…)``.
    """
    factory = _SHAPE_FACTORIES.get(name.lower())
    if factory is None:
        raise ValueError(f"unknown load shape: {name!r}; "
                         f"choose from {sorted(_SHAPE_FACTORIES)}")
    return factory(config or {})
