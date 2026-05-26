"""
cURL command importer.

Parses a single cURL invocation (single-line or multi-line with
``\\`` continuations) into a LoadDensity HTTP task dict.

Supported flags:

* ``-X / --request <method>``
* ``-H / --header 'k: v'``
* ``-d / --data / --data-raw / --data-binary <payload>``
* ``--data-urlencode <payload>``
* ``-u / --user <user:pass>``
* ``-b / --cookie <jar>``
* ``--compressed``, ``-k / --insecure``, ``-L / --location`` (recognised
  but ignored beyond setting ``verify``/``allow_redirects``)
"""

import json
import shlex
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


def _tokens(command: str) -> List[str]:
    cleaned = command.replace("\\\n", " ").replace("\n", " ")
    if cleaned.lstrip().startswith("curl"):
        cleaned = cleaned.lstrip()[4:].strip()
    return shlex.split(cleaned, posix=True)


def _split_header(value: str) -> Optional[Tuple[str, str]]:
    if ":" not in value:
        return None
    name, _, body = value.partition(":")
    return name.strip(), body.strip()


def _parse_basic_auth(value: str) -> Dict[str, str]:
    user, _, secret = value.partition(":")
    return {"type": "basic", "username": user, "password": secret}


def _try_json_body(text: str) -> Tuple[bool, Any]:
    try:
        return True, json.loads(text)
    except (TypeError, ValueError):
        return False, text


def _attach_body(task: Dict[str, Any], data_parts: List[str]) -> None:
    if not data_parts:
        return
    joined = "&".join(data_parts) if len(data_parts) > 1 else data_parts[0]
    is_json, parsed = _try_json_body(joined)
    if is_json:
        task["json"] = parsed
    else:
        task["data"] = joined


_DATA_FLAGS = frozenset({
    "-d", "--data", "--data-raw", "--data-binary", "--data-urlencode",
})


def _consume_method(task: Dict[str, Any], iterator: Iterator[str]) -> None:
    task["method"] = next(iterator, "get").lower()


def _consume_header(headers: Dict[str, str], iterator: Iterator[str]) -> None:
    parsed = _split_header(next(iterator, ""))
    if parsed:
        headers[parsed[0]] = parsed[1]


def _consume_data(task: Dict[str, Any], data_parts: List[str],
                  iterator: Iterator[str]) -> None:
    data_parts.append(next(iterator, ""))
    if task["method"] == "get":
        task["method"] = "post"


def _consume_user(task: Dict[str, Any], iterator: Iterator[str]) -> None:
    task["auth"] = _parse_basic_auth(next(iterator, ""))


def _consume_cookie(task: Dict[str, Any], iterator: Iterator[str]) -> None:
    task["cookies"] = next(iterator, "")


def _is_skip_only_flag(token: str) -> Optional[Tuple[str, Any]]:
    """Return (task-key, value) for flags that are pure on/off."""
    if token in {"-k", "--insecure"}:
        return ("verify", False)
    if token in {"-L", "--location"}:
        return ("allow_redirects", True)
    return None


def _dispatch_flag(token: str, iterator: Iterator[str], task: Dict[str, Any],
                   headers: Dict[str, str], data_parts: List[str]) -> None:
    if token in {"-X", "--request"}:
        _consume_method(task, iterator)
        return
    if token in {"-H", "--header"}:
        _consume_header(headers, iterator)
        return
    if token in _DATA_FLAGS:
        _consume_data(task, data_parts, iterator)
        return
    if token in {"-u", "--user"}:
        _consume_user(task, iterator)
        return
    if token in {"-b", "--cookie"}:
        _consume_cookie(task, iterator)
        return
    skip = _is_skip_only_flag(token)
    if skip is not None:
        task[skip[0]] = skip[1]
        return
    if token == "--compressed":
        return
    # Long opt with attached value uses "="; bare long opt consumes the next token.
    if "=" not in token:
        next(iterator, None)


def _consume(tokens: Iterable[str]) -> Dict[str, Any]:
    iterator = iter(tokens)
    task: Dict[str, Any] = {"method": "get"}
    headers: Dict[str, str] = {}
    data_parts: List[str] = []
    url: Optional[str] = None

    for token in iterator:
        if token.startswith("-"):
            _dispatch_flag(token, iterator, task, headers, data_parts)
            continue
        if url is None:
            url = token

    if headers:
        task["headers"] = headers
    _attach_body(task, data_parts)
    if url:
        task["request_url"] = url
    return task


def curl_to_task(command: str) -> Dict[str, Any]:
    """
    Parse one cURL command into a LoadDensity HTTP task dict.
    """
    return _consume(_tokens(command))
