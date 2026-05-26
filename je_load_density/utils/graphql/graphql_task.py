"""
GraphQL helper.

Lightweight adapter that converts a GraphQL task definition into a
LoadDensity HTTP task. No new user template needed — every HTTP user
template can run GraphQL via this helper.
"""

from typing import Any, Dict, Optional


def graphql_to_http_task(
    endpoint: str,
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    operation_name: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    name: Optional[str] = None,
    assertions: Optional[list] = None,
    extract: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Build a POST task that submits a GraphQL operation.

    The returned dict is a normal LoadDensity HTTP task, so all
    placeholders, assertions, and extractors work as usual.
    """
    body: Dict[str, Any] = {"query": query}
    if variables is not None:
        body["variables"] = variables
    if operation_name:
        body["operationName"] = operation_name

    task: Dict[str, Any] = {
        "method": "post",
        "request_url": endpoint,
        "json": body,
        "headers": {**(headers or {}), "Content-Type": "application/json"},
        "name": name or f"GraphQL {operation_name or 'query'}",
    }
    if assertions:
        task["assertions"] = assertions
    if extract:
        task["extract"] = extract
    return task


def extract_field(payload: Dict[str, Any], dotted_path: str) -> Any:
    """
    Pluck a value out of a parsed GraphQL response by dotted path
    (e.g. ``data.user.id``). Returns ``None`` on miss.
    """
    cursor: Any = payload
    for part in dotted_path.split("."):
        if not part:
            continue
        if isinstance(cursor, list):
            try:
                cursor = cursor[int(part)]
                continue
            except (ValueError, IndexError):
                return None
        if isinstance(cursor, dict):
            cursor = cursor.get(part)
            if cursor is None:
                return None
        else:
            return None
    return cursor
