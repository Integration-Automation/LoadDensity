"""
Sliding-window failure budget / circuit breaker.

Subscribes to Locust's ``events.request`` and tracks the proportion of
failed requests in a rolling window. Once the failure rate exceeds the
threshold *and* the window has enough samples, the next request fires
``runner.quit()`` and raises :class:`CircuitOpenError` on the main
greenlet.
"""

import collections
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Deque, Optional


class CircuitOpenError(RuntimeError):
    """Raised when the failure budget trips."""


@dataclass
class FailureBudget:
    threshold: float = 0.05
    window_seconds: float = 30.0
    min_samples: int = 50
    _events: Deque[tuple] = field(default_factory=collections.deque)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _tripped: bool = False

    def record(self, failed: bool, now: Optional[float] = None) -> None:
        timestamp = now if now is not None else time.monotonic()
        with self._lock:
            self._events.append((timestamp, bool(failed)))
            self._evict(timestamp)

    def _evict(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def failure_rate(self, now: Optional[float] = None) -> float:
        timestamp = now if now is not None else time.monotonic()
        with self._lock:
            self._evict(timestamp)
            if not self._events:
                return 0.0
            failures = sum(1 for _, failed in self._events if failed)
            return failures / len(self._events)

    def sample_count(self) -> int:
        with self._lock:
            return len(self._events)

    def is_breached(self, now: Optional[float] = None) -> bool:
        if self.sample_count() < self.min_samples:
            return False
        return self.failure_rate(now=now) > self.threshold

    def trip(self) -> None:
        self._tripped = True

    @property
    def tripped(self) -> bool:
        return self._tripped


_INSTALLED: Optional[FailureBudget] = None
_LISTENER: Optional[Callable] = None


def install_failure_budget(
    threshold: float = 0.05,
    window_seconds: float = 30.0,
    min_samples: int = 50,
    runner_quit_callback: Optional[Callable[[], None]] = None,
) -> FailureBudget:
    """
    Subscribe to Locust request events; trip the breaker when the
    sliding-window failure rate exceeds ``threshold``. The supplied
    ``runner_quit_callback`` is invoked once on breach.
    """
    global _INSTALLED, _LISTENER
    uninstall_failure_budget()
    budget = FailureBudget(threshold=threshold,
                            window_seconds=window_seconds,
                            min_samples=min_samples)

    def _listener(**kwargs):
        if budget.tripped:
            return
        budget.record(failed=kwargs.get("exception") is not None)
        if budget.is_breached():
            budget.trip()
            if runner_quit_callback is not None:
                runner_quit_callback()

    try:
        from locust import events
        events.request.add_listener(_listener)
    except ImportError:  # pragma: no cover (locust always installed)
        pass

    _INSTALLED = budget
    _LISTENER = _listener
    return budget


def uninstall_failure_budget() -> None:
    global _INSTALLED, _LISTENER
    if _LISTENER is not None:
        try:
            from locust import events
            handlers = list(getattr(events.request, "_handlers", []))
            if _LISTENER in handlers:
                handlers.remove(_LISTENER)
                events.request._handlers = handlers
        except (ImportError, AttributeError):  # pragma: no cover
            pass
    _INSTALLED = None
    _LISTENER = None


def current_budget() -> Optional[FailureBudget]:
    return _INSTALLED
