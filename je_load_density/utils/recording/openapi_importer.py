"""
OpenAPI / Swagger importer.

Generates one LoadDensity task per ``(path, method)`` defined in an
OpenAPI 3.x document. Path parameters become ``${var.<name>}`` so the
caller can supply values via ``register_variables``.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple


_PATH_PARAM = re.compile(r"\{([^}]+)\}")
_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def load_openapi(file_path: str) -> Dict[str, Any]:
    """Load an OpenAPI document. YAML support is opt-in (pyyaml soft-dep)."""
    if file_path.lower().endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore
        except ImportError as error:
            raise RuntimeError(
                "PyYAML is required for OpenAPI YAML files; install with: pip install pyyaml"
            ) from error
        with open(file_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    with open(file_path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def _first_server(spec: Dict[str, Any]) -> str:
    servers = spec.get("servers") or []
    if servers and isinstance(servers[0], dict):
        url = servers[0].get("url") or ""
        return str(url).rstrip("/")
    return ""


def _substitute_path_params(path: str) -> str:
    return _PATH_PARAM.sub(lambda m: "${var." + m.group(1) + "}", path)


def _build_url(server: str, path: str) -> str:
    parametised = _substitute_path_params(path)
    return f"{server}{parametised}" if server else parametised


def _expected_status(responses: Optional[Dict[str, Any]]) -> Optional[int]:
    if not isinstance(responses, dict):
        return None
    for code in ("200", "201", "202", "204"):
        if code in responses:
            return int(code)
    for key in responses:
        try:
            value = int(key)
        except ValueError:
            continue
        if 200 <= value < 300:
            return value
    return None


def _iter_operations(spec: Dict[str, Any]) -> List[Tuple[str, str, Dict[str, Any]]]:
    operations: List[Tuple[str, str, Dict[str, Any]]] = []
    paths = spec.get("paths") or {}
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() in _HTTP_METHODS and isinstance(operation, dict):
                operations.append((path, method.lower(), operation))
    return operations


def _operation_to_task(
    server: str, path: str, method: str, operation: Dict[str, Any],
) -> Dict[str, Any]:
    task: Dict[str, Any] = {
        "method": method,
        "request_url": _build_url(server, path),
        "name": operation.get("operationId") or f"{method.upper()} {path}",
    }
    expected = _expected_status(operation.get("responses"))
    if expected is not None:
        task["assertions"] = [{"type": "status_code", "value": expected}]
    return task


def openapi_to_tasks(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    server = _first_server(spec)
    return [_operation_to_task(server, path, method, operation)
            for path, method, operation in _iter_operations(spec)]


def openapi_to_action_json(
    spec: Dict[str, Any],
    user: str = "fast_http_user",
    user_count: int = 10,
    spawn_rate: int = 5,
    test_time: int = 60,
) -> Dict[str, Any]:
    tasks = openapi_to_tasks(spec)
    return {
        "load_density": [[
            "LD_start_test",
            {
                "user_detail_dict": {"user": user},
                "tasks": {"mode": "sequence", "tasks": tasks},
                "user_count": user_count,
                "spawn_rate": spawn_rate,
                "test_time": test_time,
            },
        ]]
    }
