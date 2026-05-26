"""
Postman v2.1 collection importer.

Walks the collection tree, converts each request into a LoadDensity HTTP
task, and optionally wraps the result in an ``LD_start_test`` action.
"""

import json
from typing import Any, Dict, Iterator, List, Optional


def load_postman_collection(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def _iter_items(node: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    for item in node.get("item", []) or []:
        if isinstance(item, dict) and "item" in item:
            yield from _iter_items(item)
        elif isinstance(item, dict):
            yield item


def _normalise_url(url: Any) -> str:
    if isinstance(url, str):
        return url
    if not isinstance(url, dict):
        return ""
    raw = url.get("raw")
    if isinstance(raw, str) and raw:
        return raw
    host = url.get("host") or []
    host_str = ".".join(host) if isinstance(host, list) else str(host)
    path = url.get("path") or []
    path_str = "/" + "/".join(path) if isinstance(path, list) else "/" + str(path)
    combined = host_str + path_str
    return combined


def _headers_to_dict(headers: Any) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if isinstance(headers, list):
        for header in headers:
            if isinstance(header, dict) and not header.get("disabled"):
                name = header.get("key") or header.get("name")
                value = header.get("value", "")
                if name:
                    result[str(name)] = str(value)
    return result


def _raw_body_to_field(body: Dict[str, Any], task: Dict[str, Any]) -> None:
    raw = body.get("raw") or ""
    language = (body.get("options") or {}).get("raw", {}).get("language", "")
    if language.lower() == "json" or _looks_like_json(raw):
        try:
            task["json"] = json.loads(raw)
            return
        except json.JSONDecodeError:
            pass
    task["data"] = raw


def _kv_collection_to_dict(items: Any) -> Dict[str, str]:
    return {
        f.get("key"): f.get("value", "")
        for f in items or []
        if isinstance(f, dict) and not f.get("disabled") and f.get("key")
    }


def _body_to_fields(body: Any, task: Dict[str, Any]) -> None:
    if not isinstance(body, dict):
        return
    mode = body.get("mode")
    if mode == "raw":
        _raw_body_to_field(body, task)
        return
    if mode == "urlencoded":
        task["data"] = _kv_collection_to_dict(body.get("urlencoded"))
        return
    if mode == "formdata":
        task["data"] = _kv_collection_to_dict(body.get("formdata"))


def _looks_like_json(text: str) -> bool:
    return text.strip().startswith(("{", "["))


def _item_to_task(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    request = item.get("request") or {}
    if not isinstance(request, dict):
        return None

    method = str(request.get("method", "get")).lower()
    url = _normalise_url(request.get("url"))
    if not url:
        return None

    task: Dict[str, Any] = {"method": method, "request_url": url,
                            "name": str(item.get("name") or url)}
    headers = _headers_to_dict(request.get("header"))
    if headers:
        task["headers"] = headers
    _body_to_fields(request.get("body"), task)
    return task


def postman_to_tasks(collection: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Walk the collection and return one task per request.
    """
    tasks: List[Dict[str, Any]] = []
    for item in _iter_items(collection):
        task = _item_to_task(item)
        if task is not None:
            tasks.append(task)
    return tasks


def postman_to_action_json(
    collection: Dict[str, Any],
    user: str = "fast_http_user",
    user_count: int = 10,
    spawn_rate: int = 5,
    test_time: int = 60,
) -> Dict[str, Any]:
    tasks = postman_to_tasks(collection)
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
