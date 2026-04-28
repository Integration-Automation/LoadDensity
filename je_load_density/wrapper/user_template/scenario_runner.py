import secrets
from typing import Any, Dict, List, Optional

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.wrapper.user_template.request_executor import (
    _normalise_tasks,
    execute_task,
)


def _coerce_tasks_payload(raw_tasks: Any) -> Dict[str, Any]:
    """
    Accept the new dict form with mode and tasks, or a bare list/dict.
    Returns {"mode": "sequence|weighted|conditional", "tasks": [...]}.
    """
    if isinstance(raw_tasks, dict) and "tasks" in raw_tasks and isinstance(raw_tasks.get("tasks"), (list, dict)):
        mode = str(raw_tasks.get("mode", "sequence")).lower()
        tasks = _normalise_tasks(raw_tasks.get("tasks"))
        return {"mode": mode, "tasks": tasks}
    return {"mode": "sequence", "tasks": _normalise_tasks(raw_tasks)}


def _condition_passes(task: Dict[str, Any]) -> bool:
    run_if = task.get("run_if")
    skip_if = task.get("skip_if")

    if run_if is not None and not _eval_condition(run_if):
        return False
    if skip_if is not None and _eval_condition(skip_if):
        return False
    return True


def _is_pair(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2


_CONDITION_OPS = {
    "equals": lambda v: v[0] == v[1] if _is_pair(v) else False,
    "not_equals": lambda v: v[0] != v[1] if _is_pair(v) else False,
    "in": lambda v: (v[0] in (v[1] or [])) if _is_pair(v) else False,
    "truthy": bool,
}


def _eval_condition(expression: Any) -> bool:
    """
    Resolve a condition. Supports:
        bool / int                          -> truthy check
        "${var.x}"                          -> truthy after resolve
        {"equals": ["${var.x}", "ok"]}      -> equality
        {"not_equals": [...]}
        {"in": ["${var.x}", ["a", "b"]]}
        {"truthy": "${var.x}"}
    """
    if isinstance(expression, (bool, int)):
        return bool(expression)
    if isinstance(expression, str):
        return bool(parameter_resolver.resolve(expression))
    if not isinstance(expression, dict):
        return False
    for op, args in expression.items():
        handler = _CONDITION_OPS.get(op.lower())
        if handler is None:
            continue
        return handler(parameter_resolver.resolve(args))
    return False


def _pick_weighted(tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    weights = [max(int(t.get("weight", 1) or 1), 0) for t in tasks]
    total = sum(weights)
    if total <= 0:
        return None
    pick = secrets.randbelow(total)
    cursor = 0
    for task, weight in zip(tasks, weights):
        cursor += weight
        if pick < cursor:
            return task
    return tasks[-1]


def run_scenario(method_map: Dict[str, Any], raw_tasks: Any) -> None:
    payload = _coerce_tasks_payload(raw_tasks)
    mode = payload["mode"]
    tasks = payload["tasks"]
    if not tasks:
        return

    if mode == "weighted":
        chosen = _pick_weighted(tasks)
        if chosen and _condition_passes(chosen):
            _safe_execute(method_map, chosen)
        return

    for task in tasks:
        if not _condition_passes(task):
            continue
        _safe_execute(method_map, task)


def _safe_execute(method_map: Dict[str, Any], task: Dict[str, Any]) -> None:
    try:
        execute_task(method_map, task)
    except Exception as error:
        load_density_logger.error(f"scenario step failed: {error!r}")
