"""
GraphQL-specific security probes.

- Introspection query (should usually be disabled in production)
- Depth attack (deeply nested query payload)
- Alias batching attack
"""

from typing import Any, Dict, List

_INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    types { name kind fields { name } }
  }
}
""".strip()


def build_introspection_payload() -> Dict[str, Any]:
    """Standard introspection probe."""
    return {"query": _INTROSPECTION_QUERY}


def build_depth_attack(depth: int = 20, leaf_field: str = "id") -> Dict[str, Any]:
    """Build a deeply nested query of the requested depth."""
    if depth <= 0:
        return {"query": f"{{ {leaf_field} }}"}
    nested = leaf_field
    for _ in range(depth):
        nested = f"node {{ {nested} }}"
    return {"query": f"query Depth {{ {nested} }}"}


def build_alias_batching_attack(field: str = "viewer", aliases: int = 100) -> Dict[str, Any]:
    """Build a single query that requests one field N times under different aliases."""
    parts: List[str] = []
    for index in range(max(1, aliases)):
        parts.append(f"a{index}: {field} {{ id }}")
    return {"query": "query Batched { " + " ".join(parts) + " }"}


def graphql_attack_pack(
    field: str = "viewer",
    depth: int = 20,
    aliases: int = 100,
) -> Dict[str, Dict[str, Any]]:
    """Return a dict of probe-name → GraphQL request payload."""
    return {
        "introspection": build_introspection_payload(),
        "depth": build_depth_attack(depth=depth, leaf_field="id"),
        "alias_batching": build_alias_batching_attack(field=field, aliases=aliases),
    }
