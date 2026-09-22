"""
Service map report — node-link JSON of {endpoint → next endpoint}.

Builds a dependency graph by reading the time-ordered test record list
and stringing together consecutive requests (heuristic — works when
``name`` reflects endpoint identity). Output is consumable by D3,
Mermaid, or Cytoscape.
"""

import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance


def build_service_map(min_weight: int = 1) -> Dict[str, Any]:
    """Return ``{nodes: [...], edges: [{source, target, weight}]}``."""
    records = list(test_record_instance.test_record_list) + list(
        test_record_instance.error_record_list
    )
    edges: Dict[tuple, int] = defaultdict(int)
    previous: Optional[str] = None
    nodes: set = set()
    for record in records:
        node = str(record.get("name") or record.get("test_url") or "")
        if not node:
            continue
        nodes.add(node)
        if previous is not None and previous != node:
            edges[(previous, node)] += 1
        previous = node
    filtered = [
        {"source": source, "target": target, "weight": weight}
        for (source, target), weight in edges.items()
        if weight >= min_weight
    ]
    return {
        "nodes": [{"id": node} for node in sorted(nodes)],
        "edges": filtered,
    }


def generate_service_map(
    report_name: str = "loaddensity-service-map",
    min_weight: int = 1,
) -> str:
    """Write the service map JSON. Returns its path."""
    graph = build_service_map(min_weight=min_weight)
    file_path = f"{report_name}.json"
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(graph, handle, ensure_ascii=False, indent=2)
    return os.path.abspath(file_path)
