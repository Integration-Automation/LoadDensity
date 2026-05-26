"""
Per-key RPS throttle.

Token-bucket limiter that caps the request rate for a named bucket.
Buckets are shared by name so multiple tasks (or workers in the same
process) can coordinate on the same cap.
"""

import threading
import time
from typing import Dict, Optional


class RpsThrottle:
    """
    Token-bucket throttle. ``acquire`` blocks until one token is
    available, then consumes it.
    """

    def __init__(self, rps: float, burst: Optional[int] = None) -> None:
        if rps <= 0:
            raise ValueError("rps must be positive")
        self._rps = float(rps)
        self._burst = float(burst if burst is not None else max(1, int(rps)))
        self._tokens = self._burst
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        sleep_for = self._consume_or_wait_seconds()
        if sleep_for > 0:
            time.sleep(sleep_for)
            self._consume_or_wait_seconds(force=True)

    def _consume_or_wait_seconds(self, force: bool = False) -> float:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._burst, self._tokens + elapsed * self._rps)
            self._last_refill = now
            if self._tokens >= 1.0 or force:
                self._tokens = max(0.0, self._tokens - 1.0)
                return 0.0
            deficit = 1.0 - self._tokens
            return deficit / self._rps


_THROTTLES: Dict[str, RpsThrottle] = {}
_THROTTLE_LOCK = threading.Lock()


def get_throttle(key: str, rps: float, burst: Optional[int] = None) -> RpsThrottle:
    """
    Return the shared throttle for ``key``; create it on first call.
    Subsequent calls ignore later ``rps`` / ``burst`` arguments — clear
    with :func:`reset_throttles` to reconfigure.
    """
    with _THROTTLE_LOCK:
        existing = _THROTTLES.get(key)
        if existing is None:
            existing = RpsThrottle(rps=rps, burst=burst)
            _THROTTLES[key] = existing
        return existing


def reset_throttles() -> None:
    with _THROTTLE_LOCK:
        _THROTTLES.clear()
