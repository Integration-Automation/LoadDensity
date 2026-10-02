"""Validated distributed policy and scoped Locust process heartbeat settings."""
import math
from dataclasses import dataclass
from threading import Lock
from typing import Mapping

from locust import runners


@dataclass(frozen=True)
class DistributedConfig:
    """Worker health policy; heartbeat timeout is quantized to native interval ticks."""

    startup_timeout: float = 60.0
    heartbeat_interval: float = 5.0
    lost_timeout: float = 15.0
    startup_policy: str = "fail"
    expected_workers: int = 0

    @classmethod
    def from_options(cls, options: Mapping[str, object]) -> "DistributedConfig":
        """Validate settings before constructing or binding a runner."""
        times = [options.get(name, default) for name, default in (
            ("worker_startup_timeout", 60), ("worker_heartbeat_interval", 5), ("worker_lost_timeout", 15))]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in times):
            raise ValueError("worker timeouts and heartbeat interval must be positive finite numbers")
        if any(not math.isfinite(value) or value <= 0 for value in times):
            raise ValueError("worker timeouts and heartbeat interval must be positive finite numbers")
        if times[2] <= times[1]:
            raise ValueError("worker_lost_timeout must be greater than worker_heartbeat_interval")
        policy = options.get("worker_startup_policy", "fail")
        if policy not in ("fail", "degraded"):
            raise ValueError("worker_startup_policy must be fail or degraded")
        count = options.get("expected_workers", 0)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("expected_workers must be a nonnegative integer")
        return cls(*map(float, times), policy, count)


class NativeHeartbeatScope:
    """Share matching native timing settings and restore them after the last runner closes.

    Locust exposes heartbeat constants at module scope, not per environment. Configurations
    cannot differ while distributed environments coexist within one process.
    """

    _lock = Lock()
    _active = 0
    _timing = None
    _previous = None

    def __init__(self, config: DistributedConfig) -> None:
        self._released = False
        timing = (config.heartbeat_interval, max(0, math.ceil(config.lost_timeout / config.heartbeat_interval) - 2))
        with self._lock:
            if self._active and self._timing != timing:
                raise ValueError("conflicting Locust heartbeat settings in the same process")
            cls = type(self)
            if not cls._active:
                cls._previous = (runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS)
                runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS = timing
                cls._timing = timing
            cls._active += 1

    def close(self) -> None:
        """Release once; a second cleanup leaves another environment's settings intact."""
        with self._lock:
            if self._released:
                return
            self._released = True
            cls = type(self)
            cls._active -= 1
            if not cls._active:
                runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS = cls._previous
                cls._timing = cls._previous = None
