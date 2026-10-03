import json
import sys
from typing import Any, Dict, Iterable, List, Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.utils.test_record.window_statistics import finite_number, latency_mean


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
    return float(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction)


def _by_name(records: Iterable[Dict[str, Any]]) -> Dict[str, List[float]]:
    grouped: Dict[str, List[float]] = {}
    for record in records:
        key = str(record.get("name") or record.get("test_url") or "unknown")
        latency = finite_number(record.get("response_time_ms"))
        if latency is None or latency < 0:
            continue
        grouped.setdefault(key, []).append(latency)
    return grouped


def build_summary(success=None, failures=None) -> Dict[str, Any]:
    """
    彙整成功與失敗紀錄為統計摘要。
    Build a summary dict of success/failure counts and per-name
    latency percentiles for charting and regression checks.
    """
    success = test_record_instance.test_record_list if success is None else success
    failures = test_record_instance.error_record_list if failures is None else failures

    all_latencies: List[float] = [
        latency
        for r in (*success, *failures)
        if (latency := finite_number(r.get("response_time_ms"))) is not None and latency >= 0
    ]

    grouped = _by_name(success)
    per_name: Dict[str, Dict[str, float]] = {}
    for name, values in grouped.items():
        per_name[name] = {
            "count": len(values),
            "min_ms": float(min(values)),
            "max_ms": float(max(values)),
            "mean_ms": latency_mean(values),
            "p50_ms": _percentile(values, 50),
            "p90_ms": _percentile(values, 90),
            "p95_ms": _percentile(values, 95),
            "p99_ms": _percentile(values, 99),
        }

    return {
        "totals": {
            "requests": len(success) + len(failures),
            "successes": len(success),
            "failures": len(failures),
            "failure_rate": (len(failures) / max(len(success) + len(failures), 1)),
        },
        "latency_overall": {
            "count": len(all_latencies),
            "p50_ms": _percentile(all_latencies, 50),
            "p90_ms": _percentile(all_latencies, 90),
            "p95_ms": _percentile(all_latencies, 95),
            "p99_ms": _percentile(all_latencies, 99),
            "max_ms": float(max(all_latencies)) if all_latencies else 0.0,
        },
        "per_name": per_name,
    }


def generate_summary_report(report_name: str = "loaddensity-summary") -> Optional[str]:
    summary = build_summary()
    path = f"{report_name}.json"
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        return path
    except OSError as error:
        print(repr(error), file=sys.stderr)
        return None
