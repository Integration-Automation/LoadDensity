"""
Auto-baseline SLA calibrator.

Reads multi-run trend data from the SQLite persistence store and
produces SLA rule suggestions that pass for the historical p95 / failure
rate at the chosen tolerance.
"""

import statistics
from typing import Any, Dict, List, Optional

from je_load_density.utils.regression.multi_run_trend import trend_runs


def calibrate_sla(
    database_path: str,
    runs_to_use: int = 10,
    tolerance_pct: float = 10.0,
    name_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Derive SLA gates that would pass for the last ``runs_to_use`` runs."""
    trend = trend_runs(database_path, limit=runs_to_use, name_filter=name_filter)
    runs = trend.get("per_run") or []
    if not runs:
        return []

    p95s = [float(run.get("p95_ms", 0)) for run in runs]
    failure_rates = [float(run.get("failure_rate", 0)) for run in runs]
    request_counts = [int(run.get("requests", 0)) for run in runs]

    headroom = 1 + tolerance_pct / 100.0
    rules: List[Dict[str, Any]] = []
    if p95s:
        rules.append({
            "type": "latency_p95",
            "value": round(max(p95s) * headroom, 2),
            "note": f"max observed * {headroom:.2f}",
        })
    if failure_rates:
        peak_failure = max(failure_rates)
        # Allow at least 1 % even if historically 0 to avoid brittle gates.
        rules.append({
            "type": "failure_rate",
            "value": round(max(peak_failure * headroom, 0.01), 4),
        })
    if request_counts:
        rules.append({
            "type": "requests",
            "op": "gte",
            "value": int(statistics.median(request_counts) // 2),
        })
    return rules
