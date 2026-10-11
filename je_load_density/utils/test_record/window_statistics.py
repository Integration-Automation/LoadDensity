"""Shared, bounded time windows for latency bands and request rates."""

import math
from collections.abc import Iterable, Mapping
from typing import Any, TypedDict


class LatencyWindow(TypedDict):
    start_time: float
    duration_seconds: float
    count: int
    rps: float
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None


def finite_number(value: Any) -> float | None:
    """Unknown, non-finite or boolean measurements never become zero latency."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def latency_mean(values: list[float]) -> float:
    """Average finite nonnegative measurements without overflowing their sum."""
    scale = max(values, default=0.0)
    if not scale:
        return 0.0
    return (math.fsum(value / scale for value in values) / len(values)) * scale


def sample_time(record: Mapping[str, Any]) -> float | None:
    """Prefer request start epoch; support canonical records and legacy ts fields."""
    for key in ("start_time", "started_at", "ts"):
        value = finite_number(record.get(key))
        if value is not None:
            return value
    return None


def percentile(values: list[float], percent: float) -> float | None:
    """Window order statistic, using Python's ties-to-even rounded index."""
    if not values:
        return None
    ordered = sorted(values)
    index = int(round(percent / 100 * (len(ordered) - 1)))
    return ordered[max(0, min(index, len(ordered) - 1))]


def _bounds(samples, start, end, duration: float, limit: int) -> tuple[float, float]:
    if start is None:
        start = math.floor(samples[0][0] / duration) * duration if samples else 0.0
    if end is None:
        end = (math.floor(samples[-1][0] / duration) + 1) * duration if samples else start
    start, end = finite_number(start), finite_number(end)
    if start is None or end is None or end < start:
        raise ValueError("window: finite end must be greater than or equal to start")
    if not math.isfinite((end - start) / duration):
        raise ValueError("window: time range is too large")
    buckets = math.ceil((end - start) / duration)
    if buckets > limit:
        start += (buckets - limit) * duration
    return start, end


def _window(start: float, duration: float, count: int, values: list[float]) -> LatencyWindow:
    return {"start_time": start, "duration_seconds": duration, "count": count, "rps": count / duration,
            "p50_ms": percentile(values, 50), "p95_ms": percentile(values, 95), "p99_ms": percentile(values, 99)}


def _optional_boundary(value) -> float | None:
    if value is None:
        return None
    number = finite_number(value)
    if number is None:
        raise ValueError("window: expected finite timestamps")
    return number


def latency_windows(records: Iterable[Mapping[str, Any]], *, start: float | None = None,
                    end: float | None = None, bucket_size_seconds: float = 1.0,
                    max_buckets: int = 120) -> list[LatencyWindow]:
    """Count all timed requests, compute measured latencies, and retain the newest buckets.

    Buckets are [start, end). Missing latency leaves a null band; empty buckets have
    zero RPS. The final partial bucket uses its actual duration. Callers pass both
    success and failure samples, never aggregate worker percentiles.
    """
    duration = finite_number(bucket_size_seconds)
    if duration is None or duration <= 0:
        raise ValueError("bucket_size_seconds: expected a finite positive number")
    if isinstance(max_buckets, bool) or not isinstance(max_buckets, int) or max_buckets <= 0:
        raise ValueError("max_buckets: expected a positive integer")
    start, end = _optional_boundary(start), _optional_boundary(end)
    if start is not None and end is not None:
        start, end = _bounds([], start, end, duration, max_buckets)
    samples = _samples(records, start, end)
    start, end = _bounds(samples, start, end, duration, max_buckets)
    groups: dict[int, tuple[int, list[float]]] = {}
    for timestamp, _index, record in samples:
        if not start <= timestamp < end:
            continue
        bucket = int((timestamp - start) // duration)
        count, values = groups.setdefault(bucket, (0, []))
        groups[bucket] = (count + 1, values)
        latency = finite_number(record.get("elapsed_ms", record.get("response_time_ms")))
        if latency is not None and latency >= 0:
            values.append(latency)
    return [_window(start + index * duration, min(duration, end - start - index * duration),
                    *groups.get(index, (0, []))) for index in range(math.ceil((end - start) / duration))]


def _samples(records, start, end):
    return sorted((timestamp, index, record) for index, record in enumerate(records)
                  if (timestamp := sample_time(record)) is not None
                  and (start is None or timestamp >= start) and (end is None or timestamp < end))
