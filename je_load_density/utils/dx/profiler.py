"""
cProfile + tracemalloc helpers.

Wraps any callable so the next run produces a profile + memory-snapshot
report. Use to find LoadDensity engine hot paths or accidental
allocations in custom user templates.
"""

import cProfile
import io
import pstats
import tracemalloc
from typing import Any, Callable, Dict, Tuple


def profile_call(
    callable_obj: Callable[..., Any],
    *args: Any,
    top_n: int = 25,
    **kwargs: Any,
) -> Tuple[Any, str]:
    """Run ``callable(*args, **kwargs)`` under cProfile. Returns (result, text)."""
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        result = callable_obj(*args, **kwargs)
    finally:
        profiler.disable()
    buffer = io.StringIO()
    pstats.Stats(profiler, stream=buffer).sort_stats("cumulative").print_stats(top_n)
    return result, buffer.getvalue()


def memory_snapshot(
    callable_obj: Callable[..., Any],
    *args: Any,
    top_n: int = 15,
    **kwargs: Any,
) -> Tuple[Any, Dict[str, Any]]:
    """Run ``callable`` under tracemalloc. Returns (result, top allocators)."""
    tracemalloc.start()
    try:
        result = callable_obj(*args, **kwargs)
        snapshot = tracemalloc.take_snapshot()
    finally:
        tracemalloc.stop()
    statistics = snapshot.statistics("lineno")[:top_n]
    return result, {
        "top_allocations": [
            {
                "trace": str(stat.traceback),
                "size_bytes": stat.size,
                "count": stat.count,
            }
            for stat in statistics
        ],
    }
