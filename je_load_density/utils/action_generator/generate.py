"""
Action JSON generator — turn an OpenAPI spec or a cURL list into a
runnable LoadDensity action JSON. Pure stdlib, so it can also be used
behind the LLM-driven MCP tool.
"""

from typing import Any, Dict, List, Optional

from je_load_density.utils.recording.curl_importer import curl_to_task
from je_load_density.utils.recording.openapi_importer import (
    load_openapi,
    openapi_to_tasks,
)


def _wrap_action(
    tasks: List[Dict[str, Any]],
    user: str,
    user_count: int,
    spawn_rate: int,
    test_time: int,
    variables: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    actions: List[Any] = []
    if variables:
        actions.append(["LD_register_variables", {"variables": variables}])
    actions.append(["LD_start_test", {
        "user_detail_dict": {"user": user},
        "user_count": user_count,
        "spawn_rate": spawn_rate,
        "test_time": test_time,
        "tasks": tasks,
    }])
    actions.append(["LD_generate_summary_report", {"report_name": "summary"}])
    return {"load_density": actions}


def generate_from_openapi(
    openapi_path: str,
    user: str = "fast_http_user",
    user_count: int = 20,
    spawn_rate: int = 5,
    test_time: int = 60,
    variables: Optional[Dict[str, Any]] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Read an OpenAPI spec and produce an action JSON document."""
    spec = load_openapi(openapi_path)
    tasks = openapi_to_tasks(spec, base_url=base_url)
    return _wrap_action(tasks, user, user_count, spawn_rate, test_time, variables)


def generate_from_curls(
    curls: List[str],
    user: str = "fast_http_user",
    user_count: int = 20,
    spawn_rate: int = 5,
    test_time: int = 60,
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Turn a list of cURL command strings into an action JSON document."""
    tasks: List[Dict[str, Any]] = []
    for command in curls:
        try:
            tasks.append(curl_to_task(command))
        except Exception:  # noqa: BLE001 - per-curl failure should not poison batch
            continue
    return _wrap_action(tasks, user, user_count, spawn_rate, test_time, variables)


def merge_actions(*docs: Dict[str, Any]) -> Dict[str, Any]:
    """Concatenate several action documents while preserving order."""
    merged: List[Any] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        actions = doc.get("load_density")
        if isinstance(actions, list):
            merged.extend(actions)
    return {"load_density": merged}
