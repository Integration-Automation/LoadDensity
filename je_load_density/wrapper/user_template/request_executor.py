import json as json_module
from typing import Any, Dict, Iterable, List, Optional, Tuple

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import parameter_resolver

_REQUEST_KW = (
    "params", "headers", "cookies", "json", "data",
    "timeout", "allow_redirects", "verify", "files",
)


def _build_kwargs(task: Dict[str, Any]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    for key in _REQUEST_KW:
        if key in task and task[key] is not None:
            kwargs[key] = task[key]

    auth = task.get("auth")
    if isinstance(auth, dict):
        auth_type = str(auth.get("type", "")).lower()
        if auth_type == "basic":
            kwargs["auth"] = (auth.get("username", ""), auth.get("password", ""))
        elif auth_type == "bearer":
            headers = dict(kwargs.get("headers") or {})
            headers["Authorization"] = f"Bearer {auth.get('token', '')}"
            kwargs["headers"] = headers

    name = task.get("name")
    if name:
        kwargs["name"] = name

    return kwargs


def _check_assertions(response: Any, assertions: Iterable[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    for assertion in assertions:
        kind = str(assertion.get("type", "")).lower()
        target = assertion.get("value")

        if kind == "status_code":
            actual = getattr(response, "status_code", None)
            if int(actual) != int(target):
                return False, f"status_code expected {target}, got {actual}"
        elif kind == "contains":
            text = getattr(response, "text", "") or ""
            if str(target) not in text:
                return False, f"body does not contain {target!r}"
        elif kind == "not_contains":
            text = getattr(response, "text", "") or ""
            if str(target) in text:
                return False, f"body unexpectedly contains {target!r}"
        elif kind == "json_path":
            path = assertion.get("path", "")
            expected = assertion.get("value")
            actual = _resolve_json_path(response, path)
            if actual != expected:
                return False, f"json_path {path} expected {expected!r}, got {actual!r}"
        elif kind == "header":
            header_name = assertion.get("name", "")
            headers = getattr(response, "headers", {}) or {}
            if headers.get(header_name) != target:
                return False, f"header {header_name} expected {target!r}, got {headers.get(header_name)!r}"
    return True, None


def _resolve_json_path(response: Any, path: str) -> Any:
    try:
        body = response.json()
    except Exception:
        return None
    cursor: Any = body
    for part in path.split("."):
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


def _apply_extractors(response: Any, extractors: Iterable[Dict[str, Any]]) -> None:
    for extractor in extractors:
        var_name = extractor.get("var")
        if not var_name:
            continue
        kind = str(extractor.get("from", "json_path")).lower()
        if kind == "json_path":
            value = _resolve_json_path(response, extractor.get("path", ""))
        elif kind == "header":
            headers = getattr(response, "headers", {}) or {}
            value = headers.get(extractor.get("name", ""))
        elif kind == "status_code":
            value = getattr(response, "status_code", None)
        else:
            value = None
        if value is not None:
            parameter_resolver.register_variable(var_name, value)


def _normalise_tasks(raw_tasks: Any) -> List[Dict[str, Any]]:
    """
    Accepts either:
        {"get": {...}, "post": {...}}  - legacy single-method-per-task
        [{"method": "get", ...}, ...]   - new list-of-tasks form
    Returns a normalised list with explicit "method".
    """
    if isinstance(raw_tasks, list):
        result = []
        for item in raw_tasks:
            if isinstance(item, dict):
                result.append(dict(item))
        return result
    if isinstance(raw_tasks, dict):
        return [{"method": method, **(payload if isinstance(payload, dict) else {})}
                for method, payload in raw_tasks.items()]
    return []


def execute_task(client: Any, method_map: Dict[str, Any], task: Dict[str, Any]) -> None:
    """
    Resolve placeholders, execute one request, run assertions, and apply extractors.
    """
    resolved = parameter_resolver.resolve(task)

    method = str(resolved.get("method", "")).lower()
    request_url = resolved.get("request_url") or resolved.get("url")
    if not method or not request_url:
        return

    http_method = method_map.get(method)
    if http_method is None:
        load_density_logger.warning(f"unsupported HTTP method: {method}")
        return

    kwargs = _build_kwargs(resolved)
    assertions = resolved.get("assertions") or []
    extractors = resolved.get("extract") or []

    if not assertions and not extractors:
        http_method(request_url, **kwargs)
        return

    catch_kwargs = dict(kwargs)
    catch_kwargs["catch_response"] = True
    with http_method(request_url, **catch_kwargs) as response:
        ok, reason = _check_assertions(response, assertions)
        if not ok:
            response.failure(reason)
        else:
            _apply_extractors(response, extractors)
            response.success()


def execute_tasks(client: Any, method_map: Dict[str, Any], raw_tasks: Any) -> None:
    for task in _normalise_tasks(raw_tasks):
        try:
            execute_task(client, method_map, task)
        except Exception as error:
            load_density_logger.error(f"task execution failed: {error!r}")


def task_body_as_json(body: Any) -> str:
    if isinstance(body, (dict, list)):
        return json_module.dumps(body)
    return str(body)
