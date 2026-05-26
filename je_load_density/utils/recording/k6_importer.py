"""
k6 script importer.

Parses the common k6 idioms (``http.get``, ``http.post``, ``http.del``
etc., plus simple ``check()`` calls) into LoadDensity tasks. The full
ES module surface is *not* supported — this is a pragmatic best-effort
that handles 80 % of real-world scripts.
"""

import re
from typing import Any, Dict, List, Optional


_HTTP_CALL = re.compile(
    r"http\.(?P<method>get|post|put|patch|del|head|options|request)\s*\(\s*"
    r"(?P<args>.*?)\s*\)\s*;?",
    re.DOTALL,
)
_STATUS_CHECK = re.compile(r"['\"]is\s+(\d{3})['\"]")


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


_BRACKET_DELTAS = {"(": (0, 1), ")": (0, -1),
                    "{": (1, 1), "}": (1, -1),
                    "[": (2, 1), "]": (2, -1)}


def _is_string_terminator(buffer: List[str], quote: str, ch: str) -> bool:
    if ch != quote:
        return False
    if len(buffer) < 2:
        return True
    return buffer[-2] != "\\"


def _update_depths(depths: List[int], ch: str) -> None:
    delta = _BRACKET_DELTAS.get(ch)
    if delta is not None:
        depths[delta[0]] += delta[1]


def _split_top_level_args(raw: str) -> List[str]:
    parts: List[str] = []
    depths = [0, 0, 0]
    buffer: List[str] = []
    in_string: Optional[str] = None

    for ch in raw:
        if in_string is not None:
            buffer.append(ch)
            if _is_string_terminator(buffer, in_string, ch):
                in_string = None
            continue
        if ch in ("'", '"', "`"):
            in_string = ch
            buffer.append(ch)
            continue
        _update_depths(depths, ch)
        if ch == "," and not any(depths):
            parts.append("".join(buffer).strip())
            buffer = []
            continue
        buffer.append(ch)

    if buffer:
        parts.append("".join(buffer).strip())
    return parts


def _normalise_method(raw_method: str) -> str:
    if raw_method == "del":
        return "delete"
    return raw_method.lower()


def _coerce_payload(value: str) -> Any:
    text = value.strip()
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            import json
            return json.loads(text.replace("'", '"'))
        except Exception:
            return text
    return _strip_quotes(text)


def _extract_status_assertion(source: str, call_end: int) -> Optional[int]:
    tail = source[call_end:call_end + 500]
    match = _STATUS_CHECK.search(tail)
    if match:
        return int(match.group(1))
    return None


def _build_task(method: str, args: List[str], expected_status: Optional[int]) -> Dict[str, Any]:
    task: Dict[str, Any] = {"method": method}
    if not args:
        return task
    task["request_url"] = _strip_quotes(args[0])
    if method == "request" and len(args) >= 2:
        task["method"] = _strip_quotes(args[0]).lower()
        task["request_url"] = _strip_quotes(args[1])
        body_index = 2
    else:
        body_index = 1
    if len(args) > body_index:
        body = _coerce_payload(args[body_index])
        if isinstance(body, (dict, list)):
            task["json"] = body
        else:
            task["data"] = body
    if expected_status is not None:
        task["assertions"] = [{"type": "status_code", "value": expected_status}]
    return task


def k6_script_to_tasks(source: str) -> List[Dict[str, Any]]:
    """
    Walk a k6 script string and return one task per ``http.*`` call.
    """
    tasks: List[Dict[str, Any]] = []
    for match in _HTTP_CALL.finditer(source):
        method = _normalise_method(match.group("method"))
        args = _split_top_level_args(match.group("args"))
        expected = _extract_status_assertion(source, match.end())
        tasks.append(_build_task(method, args, expected))
    return tasks


def k6_script_to_action_json(
    source: str,
    user: str = "fast_http_user",
    user_count: int = 10,
    spawn_rate: int = 5,
    test_time: int = 60,
) -> Dict[str, Any]:
    tasks = k6_script_to_tasks(source)
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


def load_k6_script(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as fh:
        return fh.read()
