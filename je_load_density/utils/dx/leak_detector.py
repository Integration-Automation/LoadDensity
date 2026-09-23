"""
Long-run memory leak detector.

Samples ``tracemalloc`` at intervals and reports the lines whose
allocation size has steadily grown across samples. Designed to be
plugged into a custom LoadDensity run hook.
"""

import threading
import time
import tracemalloc
from typing import Any, Dict, List


_state: Dict[str, Any] = {
    "thread": None,
    "stop": threading.Event(),
    "samples": [],
}


def _sample_loop(interval_seconds: float, max_samples: int) -> None:
    while not _state["stop"].is_set():
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        snapshot = tracemalloc.take_snapshot()
        top = snapshot.statistics("lineno")[:25]
        _state["samples"].append({
            "ts": time.time(),
            "rows": [(str(stat.traceback), stat.size, stat.count) for stat in top],
        })
        _state["samples"] = _state["samples"][-max_samples:]
        if _state["stop"].wait(interval_seconds):
            return


def start_leak_detector(
    interval_seconds: float = 30.0, max_samples: int = 20,
) -> None:
    """Begin sampling allocations every ``interval_seconds``."""
    if _state["thread"] is not None and _state["thread"].is_alive():
        return
    _state["stop"].clear()
    _state["samples"] = []
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    thread = threading.Thread(
        target=_sample_loop, args=(interval_seconds, max_samples), daemon=True,
    )
    thread.start()
    _state["thread"] = thread


def stop_leak_detector() -> None:
    """Stop sampling."""
    if _state["thread"] is None:
        return
    _state["stop"].set()
    _state["thread"].join(timeout=5)
    _state["thread"] = None
    if tracemalloc.is_tracing():
        tracemalloc.stop()


def detect_growing_allocations(min_samples: int = 3) -> List[Dict[str, Any]]:
    """Return lines whose allocation size grew monotonically across samples."""
    samples = _state.get("samples") or []
    if len(samples) < min_samples:
        return []
    growth: Dict[str, List[int]] = {}
    for sample in samples:
        for trace, size, _count in sample["rows"]:
            growth.setdefault(trace, []).append(size)
    suspects: List[Dict[str, Any]] = []
    for trace, sizes in growth.items():
        if len(sizes) < min_samples:
            continue
        if all(b >= a for a, b in zip(sizes, sizes[1:])) and sizes[-1] > sizes[0]:
            suspects.append({
                "trace": trace,
                "first_bytes": sizes[0],
                "last_bytes": sizes[-1],
                "growth_bytes": sizes[-1] - sizes[0],
            })
    suspects.sort(key=lambda row: row["growth_bytes"], reverse=True)
    return suspects
