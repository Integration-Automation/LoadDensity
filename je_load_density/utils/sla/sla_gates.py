"""
Latency / failure-rate SLA gates.

Evaluate a list of SLA rules against ``build_summary()`` output.
Each rule has a ``type``, an optional ``name`` (per-endpoint),
``op`` (``lt`` / ``lte`` / ``gt`` / ``gte``, default ``lte``),
and a ``value``.

Supported types:

* ``latency_p50``, ``latency_p90``, ``latency_p95``, ``latency_p99``
  — milliseconds. Default scope is overall; pass ``name`` for one
  endpoint.
* ``latency_mean`` — millisecond mean (per-name only).
* ``failure_rate`` — fraction in [0, 1].
* ``requests`` — minimum request count.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

from je_load_density.utils.exception.exceptions import LoadDensityAssertException
from je_load_density.utils.generate_report.generate_summary_report import build_summary


_OPS: Dict[str, Callable[[float, float], bool]] = {
    "lt":  lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt":  lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
}


@dataclass
class SlaResult:
    passed: bool
    rule: Dict[str, Any]
    actual: Optional[float]
    reason: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "rule": self.rule,
            "actual": self.actual,
            "reason": self.reason,
        }


@dataclass
class _Lookup:
    summary: Dict[str, Any]
    per_name_metrics: Dict[str, str] = field(default_factory=lambda: {
        "latency_p50": "p50_ms",
        "latency_p90": "p90_ms",
        "latency_p95": "p95_ms",
        "latency_p99": "p99_ms",
        "latency_mean": "mean_ms",
        "requests": "count",
    })
    overall_metrics: Dict[str, str] = field(default_factory=lambda: {
        "latency_p50": "p50_ms",
        "latency_p90": "p90_ms",
        "latency_p95": "p95_ms",
        "latency_p99": "p99_ms",
    })


def _per_name_value(lookup: _Lookup, rule_type: str, name: str) -> Optional[float]:
    name_block = lookup.summary.get("per_name", {}).get(name)
    if not isinstance(name_block, dict):
        return None
    key = lookup.per_name_metrics.get(rule_type)
    if key is None:
        return None
    value = name_block.get(key)
    return None if value is None else float(value)


def _overall_value(lookup: _Lookup, rule_type: str) -> Optional[float]:
    if rule_type == "failure_rate":
        value = lookup.summary.get("totals", {}).get("failure_rate")
        return None if value is None else float(value)
    if rule_type == "requests":
        value = lookup.summary.get("totals", {}).get("requests")
        return None if value is None else float(value)
    key = lookup.overall_metrics.get(rule_type)
    if key is None:
        return None
    value = lookup.summary.get("latency_overall", {}).get(key)
    return None if value is None else float(value)


def _lookup_value(lookup: _Lookup, rule: Dict[str, Any]) -> Optional[float]:
    rule_type = str(rule.get("type", ""))
    name = rule.get("name")
    if name:
        return _per_name_value(lookup, rule_type, name)
    return _overall_value(lookup, rule_type)


def _check_rule(lookup: _Lookup, rule: Dict[str, Any]) -> SlaResult:
    op = str(rule.get("op", "lte")).lower()
    handler = _OPS.get(op)
    if handler is None:
        return SlaResult(False, rule, None, f"unsupported op {op!r}")

    expected = rule.get("value")
    if expected is None:
        return SlaResult(False, rule, None, "rule missing 'value'")

    actual = _lookup_value(lookup, rule)
    if actual is None:
        return SlaResult(False, rule, None, "metric not available in summary")

    passed = handler(actual, float(expected))
    if passed:
        return SlaResult(True, rule, actual)
    return SlaResult(False, rule, actual,
                     f"{rule.get('type')}({rule.get('name', 'overall')})={actual} not {op} {expected}")


def evaluate_sla(
    rules: Iterable[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate every rule against the supplied summary (or
    ``build_summary()`` when omitted). Returns a list of result dicts.
    """
    lookup = _Lookup(summary=summary if summary is not None else build_summary())
    return [_check_rule(lookup, dict(rule)).as_dict() for rule in rules]


def assert_sla(
    rules: Iterable[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate ``rules`` and raise ``LoadDensityAssertException`` on any
    failure. Returns the full result list on success.
    """
    results = evaluate_sla(rules, summary=summary)
    failures = [r for r in results if not r["passed"]]
    if failures:
        reasons = "; ".join(f["reason"] for f in failures)
        raise LoadDensityAssertException(f"SLA gates failed: {reasons}")
    return results
