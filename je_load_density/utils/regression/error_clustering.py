"""
Error clustering.

Groups error_record_list entries by a normalised "signature" so a long
list of distinct exception messages collapses into a small set of
clusters with sample messages + counts.
"""

import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

_HEX_RE = re.compile(r"0x[0-9a-fA-F]+")
_NUM_RE = re.compile(r"\b\d+\b")
_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")


def _signature(message: str) -> str:
    text = _UUID_RE.sub("<uuid>", message)
    text = _HEX_RE.sub("<hex>", text)
    text = _NUM_RE.sub("<n>", text)
    text = _QUOTED_RE.sub("<str>", text)
    return text.strip()[:200]


def cluster_errors(records: Optional[Iterable[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Return a list of error clusters ordered by descending count."""
    if records is None:
        from je_load_density.utils.test_record.test_record_class import (
            test_record_instance,
        )
        records = test_record_instance.error_record_list

    buckets: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "samples": [], "names": set()},
    )
    for record in records:
        message = str(record.get("error", "") or record.get("status_code", "") or "")
        signature = _signature(message)
        bucket = buckets[signature]
        bucket["count"] += 1
        bucket["names"].add(str(record.get("name", "")))
        if len(bucket["samples"]) < 3:
            bucket["samples"].append(message)

    clusters: List[Dict[str, Any]] = []
    for signature, bucket in buckets.items():
        clusters.append({
            "signature": signature,
            "count": bucket["count"],
            "names": sorted(bucket["names"]),
            "samples": bucket["samples"],
        })
    clusters.sort(key=lambda item: item["count"], reverse=True)
    return clusters
