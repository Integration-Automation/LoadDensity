import json
import re
from typing import Any, Dict, Iterable, List, Optional

_NON_REQUEST_HEADERS = frozenset({
    "host", "content-length", "connection",
    ":authority", ":method", ":path", ":scheme",
})


def load_har(file_path: str) -> Dict[str, Any]:
    """
    讀取 HAR JSON 檔。
    Read a HAR JSON file from disk.
    """
    with open(file_path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def _extract_request_headers(raw_headers: Any) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for header in raw_headers or []:
        name = str(header.get("name", "")).strip()
        value = header.get("value", "")
        if name and name.lower() not in _NON_REQUEST_HEADERS:
            headers[name] = value
    return headers


def _attach_post_body(task: Dict[str, Any], post_data: Dict[str, Any]) -> None:
    mime = str(post_data.get("mimeType", "")).lower()
    text = post_data.get("text")
    params = post_data.get("params")

    if "application/json" in mime and text:
        try:
            task["json"] = json.loads(text)
        except json.JSONDecodeError:
            task["data"] = text
        return
    if params:
        task["data"] = {p.get("name"): p.get("value") for p in params if p.get("name")}
        return
    if text:
        task["data"] = text


def _entry_to_task(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    request = entry.get("request") or {}
    method = str(request.get("method", "")).lower()
    url = request.get("url")
    if not method or not url:
        return None

    task: Dict[str, Any] = {
        "method": method,
        "request_url": url,
        "name": f"{method.upper()} {_path_only(url)}",
    }
    headers = _extract_request_headers(request.get("headers"))
    if headers:
        task["headers"] = headers

    _attach_post_body(task, request.get("postData") or {})

    expected_status = (entry.get("response") or {}).get("status")
    if isinstance(expected_status, int) and expected_status:
        task["assertions"] = [{"type": "status_code", "value": expected_status}]

    return task


def _path_only(url: str) -> str:
    match = re.match(r"^[a-zA-Z]+://[^/]+(/.*)?$", url)
    return match.group(1) or "/" if match else url


def _filter_entries(
    entries: Iterable[Dict[str, Any]],
    include: Optional[List[str]],
    exclude: Optional[List[str]],
) -> Iterable[Dict[str, Any]]:
    include_patterns = [re.compile(p) for p in (include or [])]
    exclude_patterns = [re.compile(p) for p in (exclude or [])]

    for entry in entries:
        url = ((entry.get("request") or {}).get("url")) or ""
        if include_patterns and not any(p.search(url) for p in include_patterns):
            continue
        if any(p.search(url) for p in exclude_patterns):
            continue
        yield entry


def har_to_tasks(
    har: Dict[str, Any],
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    將 HAR 轉成任務清單。
    Convert a HAR document into a list of LoadDensity tasks.
    """
    entries = ((har.get("log") or {}).get("entries")) or []
    tasks: List[Dict[str, Any]] = []
    for entry in _filter_entries(entries, include, exclude):
        task = _entry_to_task(entry)
        if task is not None:
            tasks.append(task)
    return tasks


def har_to_action_json(
    har: Dict[str, Any],
    user: str = "fast_http_user",
    user_count: int = 10,
    spawn_rate: int = 5,
    test_time: int = 60,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    將 HAR 轉成 LoadDensity action JSON。
    Convert a HAR document into a complete action JSON ready to feed
    into execute_action.
    """
    tasks = har_to_tasks(har, include=include, exclude=exclude)
    return {
        "load_density": [
            [
                "LD_start_test",
                {
                    "user_detail_dict": {"user": user},
                    "tasks": {"mode": "sequence", "tasks": tasks},
                    "user_count": user_count,
                    "spawn_rate": spawn_rate,
                    "test_time": test_time,
                },
            ]
        ]
    }
