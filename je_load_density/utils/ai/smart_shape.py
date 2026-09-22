"""
Smart load shape — binary search to find the breaking point.

Given a probe callable that runs N users for K seconds and returns the
observed failure rate, ``find_breaking_point`` does a binary search
between ``min_users`` and ``max_users`` for the largest user count
whose failure rate stays under ``failure_threshold``.
"""

from typing import Any, Callable, Dict, List


def find_breaking_point(
    probe: Callable[[int], float],
    min_users: int = 1,
    max_users: int = 1000,
    failure_threshold: float = 0.01,
    max_iterations: int = 12,
) -> Dict[str, Any]:
    """
    Binary search for the largest user count under ``failure_threshold``.

    ``probe(users) -> failure_rate`` (0..1). Returns the largest
    "safe" user count plus the iteration history. ``safe_users`` is 0
    when no probed count stayed under the threshold, including
    ``min_users`` itself.
    """
    if min_users <= 0 or max_users <= min_users:
        raise ValueError("invalid user bounds")
    if not 0 <= failure_threshold <= 1:
        raise ValueError("failure_threshold must be in [0,1]")

    history: List[Dict[str, Any]] = []
    lo = min_users
    hi = max_users
    last_safe = 0
    for _ in range(max_iterations):
        if lo > hi:
            break
        mid = (lo + hi) // 2
        failure_rate = float(probe(mid))
        history.append({"users": mid, "failure_rate": failure_rate})
        if failure_rate <= failure_threshold:
            last_safe = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return {"safe_users": last_safe, "history": history}
