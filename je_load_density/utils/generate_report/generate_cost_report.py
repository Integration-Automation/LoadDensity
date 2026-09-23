"""
Cloud cost calculator — estimate per-run spend.

Operator provides hourly rates per worker tier; the report records run
duration and the worker count specified by the caller and produces a
cost breakdown JSON.
"""

import json
import os
from typing import Any, Dict, Optional


def estimate_run_cost(
    duration_seconds: float,
    workers: int,
    hourly_rate_usd: float,
    egress_gb: float = 0.0,
    egress_rate_usd_per_gb: float = 0.09,
    extra_costs_usd: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Return the cost breakdown for one run."""
    hours = duration_seconds / 3600.0
    compute_usd = hourly_rate_usd * workers * hours
    egress_usd = egress_gb * egress_rate_usd_per_gb
    extras = dict(extra_costs_usd or {})
    total = compute_usd + egress_usd + sum(extras.values())
    return {
        "duration_seconds": duration_seconds,
        "workers": workers,
        "hourly_rate_usd": hourly_rate_usd,
        "compute_usd": round(compute_usd, 4),
        "egress_gb": egress_gb,
        "egress_usd": round(egress_usd, 4),
        "extras_usd": {k: round(v, 4) for k, v in extras.items()},
        "total_usd": round(total, 4),
    }


def generate_cost_report(
    report_name: str = "loaddensity-cost",
    duration_seconds: float = 0.0,
    workers: int = 1,
    hourly_rate_usd: float = 0.05,
    egress_gb: float = 0.0,
    egress_rate_usd_per_gb: float = 0.09,
    extras_usd: Optional[Dict[str, float]] = None,
) -> str:
    """Write the cost breakdown JSON. Returns its path."""
    breakdown = estimate_run_cost(
        duration_seconds=duration_seconds,
        workers=workers,
        hourly_rate_usd=hourly_rate_usd,
        egress_gb=egress_gb,
        egress_rate_usd_per_gb=egress_rate_usd_per_gb,
        extra_costs_usd=extras_usd,
    )
    file_path = f"{report_name}.json"
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(breakdown, handle, ensure_ascii=False, indent=2)
    return os.path.abspath(file_path)
