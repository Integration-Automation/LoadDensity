"""
Cross-run regression diff.

Loads two runs from a SQLite persistence database and compares per-name
latency percentiles + failure rate. Returns a structured diff so CI can
gate on regressions above a configurable tolerance.
"""

import statistics
from typing import Any, Dict, Iterable, List, Optional

from je_load_density.utils.test_record.sqlite_persistence import fetch_run_records


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(values)
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = rank - lower
    return float(
        sorted_values[lower]
        + (sorted_values[upper] - sorted_values[lower]) * fraction
    )


def _name_for(record: Dict[str, Any]) -> str:
    return str(record.get("name") or record.get("test_url") or "unknown")


def summarise_records(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Aggregate raw records into ``{name: {count, failures, p50, p95, p99, mean}}``.
    """
    buckets: Dict[str, Dict[str, Any]] = {}
    for record in records:
        name = _name_for(record)
        bucket = buckets.setdefault(name, {"latencies": [], "failures": 0, "count": 0})
        bucket["count"] += 1
        if str(record.get("outcome", "")).lower() == "failure":
            bucket["failures"] += 1
        latency = record.get("response_time_ms")
        if latency is not None:
            try:
                bucket["latencies"].append(float(latency))
            except (TypeError, ValueError):
                continue

    result: Dict[str, Dict[str, float]] = {}
    for name, bucket in buckets.items():
        latencies = bucket["latencies"]
        result[name] = {
            "count": float(bucket["count"]),
            "failures": float(bucket["failures"]),
            "failure_rate": bucket["failures"] / max(bucket["count"], 1),
            "mean_ms": float(statistics.fmean(latencies)) if latencies else 0.0,
            "p50_ms": _percentile(latencies, 50),
            "p95_ms": _percentile(latencies, 95),
            "p99_ms": _percentile(latencies, 99),
        }
    return result


def _delta(baseline: Optional[float], current: Optional[float]) -> Dict[str, float]:
    base = float(baseline or 0.0)
    cur = float(current or 0.0)
    abs_delta = cur - base
    pct = (abs_delta / base) if base > 0 else None
    return {"baseline": base, "current": cur, "abs": abs_delta,
            "pct": pct if pct is not None else 0.0}


def _classify(deltas: Dict[str, Dict[str, float]],
              tolerance: float) -> List[str]:
    regressed: List[str] = []
    for metric, change in deltas.items():
        if change["pct"] is None:
            continue
        if change["pct"] > tolerance:
            regressed.append(metric)
    return regressed


def diff_runs(
    database_path: str,
    baseline_run_id: int,
    current_run_id: int,
    tolerance: float = 0.10,
) -> Dict[str, Any]:
    """
    Compare two runs in ``database_path``. ``tolerance`` is the
    fractional increase allowed (e.g. ``0.10`` = 10 %). Metrics that
    breach the tolerance are listed under ``regressions``.
    """
    baseline = summarise_records(fetch_run_records(database_path, baseline_run_id))
    current = summarise_records(fetch_run_records(database_path, current_run_id))

    names = sorted(set(baseline) | set(current))
    per_name: Dict[str, Dict[str, Any]] = {}
    regressions: List[Dict[str, Any]] = []
    metrics_of_interest = ("p50_ms", "p95_ms", "p99_ms", "failure_rate", "mean_ms")

    for name in names:
        base = baseline.get(name) or {}
        cur = current.get(name) or {}
        deltas = {m: _delta(base.get(m), cur.get(m)) for m in metrics_of_interest}
        per_name[name] = {"deltas": deltas}
        regressed = _classify(deltas, tolerance)
        if regressed:
            regressions.append({"name": name, "metrics": regressed})

    return {
        "baseline_run_id": baseline_run_id,
        "current_run_id": current_run_id,
        "tolerance": tolerance,
        "per_name": per_name,
        "regressions": regressions,
        "has_regressions": bool(regressions),
    }
