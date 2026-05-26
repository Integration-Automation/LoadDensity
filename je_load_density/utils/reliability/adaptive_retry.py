"""
Adaptive retry with exponential backoff, jitter, and per-error-class
budgets.

The policy classifies an exception into one of three buckets:

* ``transient``  — retry liberally (default 5×).
* ``flaky``      — retry sparingly (default 2×).
* ``permanent``  — do not retry; the error is the answer.

``run_with_retry(fn, policy=...)`` wraps a callable. Callers can also
classify their own exception types by passing ``classifier=`` to
:class:`AdaptiveRetryPolicy`.
"""

import secrets
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


_DEFAULT_TRANSIENT = (
    "ConnectionError", "ConnectTimeout", "ReadTimeout", "Timeout",
    "ConnectionResetError", "ConnectionRefusedError", "TimeoutError",
    "RemoteDisconnected", "ProtocolError",
)
_DEFAULT_FLAKY = (
    "AssertionError", "JSONDecodeError",
)


def classify_error(error: BaseException) -> str:
    name = type(error).__name__
    if name in _DEFAULT_TRANSIENT:
        return "transient"
    if name in _DEFAULT_FLAKY:
        return "flaky"
    return "permanent"


@dataclass
class RetryDecision:
    attempt: int
    classification: str
    delay_seconds: float
    will_retry: bool


@dataclass
class AdaptiveRetryPolicy:
    transient_budget: int = 5
    flaky_budget: int = 2
    permanent_budget: int = 0
    base_delay: float = 0.1
    max_delay: float = 5.0
    backoff_factor: float = 2.0
    jitter: float = 0.25
    classifier: Callable[[BaseException], str] = classify_error
    _counts: Dict[str, int] = field(default_factory=dict)

    def budget_for(self, classification: str) -> int:
        return {
            "transient": self.transient_budget,
            "flaky": self.flaky_budget,
            "permanent": self.permanent_budget,
        }.get(classification, 0)

    def reset(self) -> None:
        self._counts = {}

    def decide(self, error: BaseException, attempt: int) -> RetryDecision:
        classification = self.classifier(error)
        budget = self.budget_for(classification)
        used = self._counts.get(classification, 0)
        will_retry = used < budget
        delay = self._next_delay(attempt) if will_retry else 0.0
        if will_retry:
            self._counts[classification] = used + 1
        return RetryDecision(attempt, classification, delay, will_retry)

    def _next_delay(self, attempt: int) -> float:
        raw = self.base_delay * (self.backoff_factor ** max(0, attempt - 1))
        capped = min(self.max_delay, raw)
        if self.jitter <= 0:
            return capped
        span_ms = max(1, int(capped * self.jitter * 1000))
        offset = secrets.randbelow(span_ms) / 1000.0
        return capped + offset


def run_with_retry(
    fn: Callable[[], object],
    policy: Optional[AdaptiveRetryPolicy] = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> object:
    """
    Run ``fn`` under ``policy``. Returns ``fn``'s result on success;
    re-raises the last exception once the budget is exhausted.
    """
    chosen = policy or AdaptiveRetryPolicy()
    chosen.reset()
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except BaseException as error:
            decision = chosen.decide(error, attempt)
            if not decision.will_retry:
                raise
            sleeper(decision.delay_seconds)
