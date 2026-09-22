"""
Closed-loop auto-tuner for ``spawn_rate`` and ``user_count``.

Iterates short test windows, adjusts the parameters proportionally so
p95 latency approaches a target. Pure deterministic controller —
intentionally not ML-based to keep the dependency footprint flat.
"""

from typing import Any, Callable, Dict, List, Optional


class AutoTuner:
    """Proportional controller targeting a p95 latency budget."""

    def __init__(
        self,
        target_p95_ms: float,
        initial_users: int = 10,
        initial_spawn_rate: int = 5,
        step_seconds: float = 30.0,
        max_users: int = 1000,
        min_users: int = 1,
        gain: float = 0.5,
    ) -> None:
        if target_p95_ms <= 0:
            raise ValueError("target_p95_ms must be positive")
        self.target_p95_ms = float(target_p95_ms)
        self.users = int(initial_users)
        self.spawn_rate = int(initial_spawn_rate)
        self.step_seconds = float(step_seconds)
        self.max_users = int(max_users)
        self.min_users = int(min_users)
        self.gain = float(gain)
        self.history: List[Dict[str, Any]] = []

    def next_step(self, measured_p95_ms: float) -> Dict[str, Any]:
        """Given the latest measured p95, return updated users/spawn_rate."""
        if measured_p95_ms <= 0:
            measured_p95_ms = self.target_p95_ms
        error = (self.target_p95_ms - measured_p95_ms) / self.target_p95_ms
        adjustment = 1.0 + self.gain * error
        new_users = max(self.min_users, min(self.max_users, int(self.users * adjustment)))
        if new_users == self.users:
            new_users += 1 if error > 0 else -1 if error < 0 else 0
        new_users = max(self.min_users, min(self.max_users, new_users))
        self.users = new_users
        self.spawn_rate = max(1, int(self.users / 5))
        self.history.append({
            "measured_p95_ms": measured_p95_ms,
            "target_p95_ms": self.target_p95_ms,
            "users": self.users,
            "spawn_rate": self.spawn_rate,
        })
        return {"users": self.users, "spawn_rate": self.spawn_rate}

    def run(
        self,
        iterations: int,
        measure_step: Callable[[int, int, float], float],
    ) -> List[Dict[str, Any]]:
        """
        Drive ``iterations`` rounds.

        ``measure_step(users, spawn_rate, step_seconds) -> measured_p95_ms``
        is supplied by the caller (it actually runs the load test).
        """
        for _ in range(iterations):
            measured = float(measure_step(self.users, self.spawn_rate, self.step_seconds))
            self.next_step(measured)
        return self.history
