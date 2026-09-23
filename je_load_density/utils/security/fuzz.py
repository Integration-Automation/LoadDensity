"""
Mutation-based fuzzing primitives.

Generates payload variants from a seed value (string, JSON, query
parameters) that can be plugged into any existing HTTP task. Pure stdlib
so it adds no install footprint.
"""

import json as json_module
import secrets
from typing import Any, Dict, List, Sequence

_BAD_BYTES = (
    "",
    "'",
    '"',
    "<script>",
    "../",
    "%00",
    " ",
    "0",
    "-1",
    "9" * 32,
)


def _mutate_string(seed: str) -> List[str]:
    """The seed first, then distinct mutations of it (duplicates, e.g. for an empty seed, are dropped)."""
    candidates = [
        seed,
        seed + _BAD_BYTES[secrets.randbelow(len(_BAD_BYTES))],
        seed * 2,
        seed[::-1],
        secrets.token_hex(4),
        "",
    ]
    return list(dict.fromkeys(candidates))


def mutate_string(seed: str, count: int = 5) -> List[str]:
    """Return up to ``count`` mutated copies of ``seed``."""
    variants = _mutate_string(seed)
    if count >= len(variants):
        return variants
    return variants[:count]


def mutate_json(seed: Dict[str, Any], count: int = 5) -> List[Dict[str, Any]]:
    """Return mutated dict variants. Each variant flips/removes one field."""
    variants: List[Dict[str, Any]] = []
    keys = list(seed.keys())
    if not keys:
        # Nothing to flip: return unchanged copies so callers still get ``count`` variants.
        return [dict(seed) for _ in range(count)]
    for _ in range(count):
        copy = dict(seed)
        key = keys[secrets.randbelow(len(keys))]
        choice = secrets.randbelow(4)
        if choice == 0:
            copy.pop(key, None)
        elif choice == 1:
            copy[key] = None
        elif choice == 2:
            copy[key] = _BAD_BYTES[secrets.randbelow(len(_BAD_BYTES))]
        else:
            copy[key] = secrets.token_hex(8)
        variants.append(copy)
    return variants


def fuzz_query_string(params: Dict[str, str], count: int = 5) -> List[Dict[str, str]]:
    """Return mutated copies of a query parameter dict."""
    variants: List[Dict[str, str]] = []
    keys = list(params.keys())
    for _ in range(count):
        copy = dict(params)
        if keys:
            key = keys[secrets.randbelow(len(keys))]
            copy[key] = _BAD_BYTES[secrets.randbelow(len(_BAD_BYTES))]
        copy[secrets.token_hex(3)] = secrets.token_hex(4)
        variants.append(copy)
    return variants


def expand_task_fuzz(task: Dict[str, Any], count: int = 5) -> List[Dict[str, Any]]:
    """
    Expand a task into ``count`` fuzzed variants.

    Mutates JSON body, query params, and one header value. Leaves the
    URL untouched so requests still resolve to the same endpoint.
    """
    variants: List[Dict[str, Any]] = []
    json_seed = task.get("json")
    bodies = mutate_json(json_seed, count) if isinstance(json_seed, dict) else [None] * count
    queries = (
        fuzz_query_string(task["params"], count)
        if isinstance(task.get("params"), dict)
        else [None] * count
    )
    for index in range(count):
        variant = dict(task)
        if bodies[index] is not None:
            variant["json"] = bodies[index]
        if queries[index] is not None:
            variant["params"] = queries[index]
        variants.append(variant)
    return variants


def render_fuzz_payload(seed: str) -> str:
    """Return one payload as JSON-encoded text (useful for raw HTTP bodies)."""
    return json_module.dumps(list(_BAD_BYTES) + list(_mutate_string(seed)))


BAD_BYTES: Sequence[str] = _BAD_BYTES
