"""
Multi-run trend report.

Pulls the latest N runs from the SQLite persistence store and computes
per-name latency / failure-rate trend rows. Output is a plain dict so
it can be fed into JSON / CSV / dashboard pipelines.
"""

import sqlite3
import statistics
from typing import Any, Dict, List, Optional


def _connect(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(pct / 100.0 * (len(ordered) - 1)))))
    return float(ordered[index])


def _run_summary(rows: List[sqlite3.Row]) -> Dict[str, Any]:
    latencies = [float(row["response_time_ms"] or 0) for row in rows]
    failures = sum(1 for row in rows if row["outcome"] == "failure")
    return {
        "requests": len(rows),
        "failures": failures,
        "failure_rate": (failures / len(rows)) if rows else 0.0,
        "mean_ms": statistics.fmean(latencies) if latencies else 0.0,
        "p50_ms": _percentile(latencies, 50),
        "p95_ms": _percentile(latencies, 95),
        "p99_ms": _percentile(latencies, 99),
    }


def _by_name(rows: List[sqlite3.Row]) -> Dict[str, List[sqlite3.Row]]:
    grouped: Dict[str, List[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(str(row["name"] or ""), []).append(row)
    return grouped


def trend_runs(
    database_path: str,
    limit: int = 10,
    name_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a trend snapshot across the latest ``limit`` runs."""
    connection = _connect(database_path)
    try:
        runs = list(connection.execute(
            "SELECT id, started_at, label FROM load_density_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ))
        per_run: List[Dict[str, Any]] = []
        per_name_trend: Dict[str, List[Dict[str, Any]]] = {}
        for run in reversed(runs):
            cursor = connection.execute(
                "SELECT outcome, name, response_time_ms FROM load_density_records "
                "WHERE run_id = ?",
                (run["id"],),
            )
            rows = list(cursor)
            if name_filter:
                rows = [row for row in rows if name_filter in (row["name"] or "")]
            overall = _run_summary(rows)
            per_run.append({
                "run_id": run["id"],
                "started_at": run["started_at"],
                "label": run["label"],
                **overall,
            })
            for name, name_rows in _by_name(rows).items():
                per_name_trend.setdefault(name, []).append({
                    "run_id": run["id"],
                    **_run_summary(name_rows),
                })
        return {"per_run": per_run, "per_name": per_name_trend}
    finally:
        connection.close()
