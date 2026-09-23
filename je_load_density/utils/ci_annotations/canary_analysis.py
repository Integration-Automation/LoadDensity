"""
Canary analysis helper.

Compares the latest run summary against the baseline summary using the
existing SLA gate rules; emits a structured verdict that a deployment
controller (Argo Rollouts, Flagger, Spinnaker, custom) can read.
"""

from typing import Any, Dict, List

from je_load_density.utils.sla.sla_gates import evaluate_sla


def canary_verdict(
    baseline_summary: Dict[str, Any],
    candidate_summary: Dict[str, Any],
    sla_rules: List[Dict[str, Any]],
    tolerance_pct: float = 10.0,
) -> Dict[str, Any]:
    """
    Run the SLA rules against ``candidate_summary`` and compare key
    latency / failure metrics against ``baseline_summary``.

    Returns ``{"verdict": "promote"|"rollback", "reasons": [...], "diff": {...}}``.
    """
    sla_findings = evaluate_sla(sla_rules, summary=candidate_summary)
    reasons: List[str] = []
    if sla_findings:
        reasons.extend(f"SLA: {item['rule']}" for item in sla_findings)

    diff = _compare(baseline_summary, candidate_summary, tolerance_pct)
    for note in diff:
        if note["status"] == "regression":
            reasons.append(
                f"regression: {note['metric']} {note['baseline']:.2f} -> "
                f"{note['candidate']:.2f}"
            )

    return {
        "verdict": "rollback" if reasons else "promote",
        "reasons": reasons,
        "sla_findings": sla_findings,
        "diff": diff,
    }


def _compare(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
    tolerance_pct: float,
) -> List[Dict[str, Any]]:
    notes: List[Dict[str, Any]] = []
    headroom = 1 + tolerance_pct / 100.0
    base_totals = baseline.get("totals", {})
    cand_totals = candidate.get("totals", {})
    notes.append(_check(
        "failure_rate",
        float(base_totals.get("failure_rate", 0)),
        float(cand_totals.get("failure_rate", 0)),
        headroom,
        higher_is_worse=True,
    ))
    base_latency = baseline.get("latency_overall", {})
    cand_latency = candidate.get("latency_overall", {})
    for key in ("p50_ms", "p95_ms", "p99_ms"):
        notes.append(_check(
            key,
            float(base_latency.get(key, 0)),
            float(cand_latency.get(key, 0)),
            headroom,
            higher_is_worse=True,
        ))
    return notes


def _check(
    metric: str,
    baseline_value: float,
    candidate_value: float,
    headroom: float,
    higher_is_worse: bool,
) -> Dict[str, Any]:
    threshold = baseline_value * headroom if higher_is_worse else baseline_value / headroom
    breached = (
        candidate_value > threshold if higher_is_worse else candidate_value < threshold
    )
    return {
        "metric": metric,
        "baseline": baseline_value,
        "candidate": candidate_value,
        "threshold": threshold,
        "status": "regression" if breached and baseline_value > 0 else "ok",
    }
