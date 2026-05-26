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
from typing import Any, Dict, Iterable, List, Optional, Tuple


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
    user, _, password = value.partition(":")
    return {"type": "basic", "username": user, "password": password}


def _try_json_body(text: str) -> Tuple[bool, Any]:
    try:
        return True, json.loads(text)
    except (TypeError, ValueError):
        return False, text


def _consume(tokens: Iterable[str]) -> Dict[str, Any]:
    iterator = iter(tokens)
    task: Dict[str, Any] = {"method": "get"}
    headers: Dict[str, str] = {}
    data_parts: List[str] = []
    url: Optional[str] = None

    for token in iterator:
        if token in {"-X", "--request"}:
            task["method"] = next(iterator, "get").lower()
        elif token in {"-H", "--header"}:
            header = _split_header(next(iterator, ""))
            if header:
                headers[header[0]] = header[1]
        elif token in {"-d", "--data", "--data-raw", "--data-binary", "--data-urlencode"}:
            data_parts.append(next(iterator, ""))
            if task["method"] == "get":
                task["method"] = "post"
        elif token in {"-u", "--user"}:
            task["auth"] = _parse_basic_auth(next(iterator, ""))
        elif token in {"-b", "--cookie"}:
            task["cookies"] = next(iterator, "")
        elif token == "-k" or token == "--insecure":
            task["verify"] = False
        elif token in {"-L", "--location"}:
            task["allow_redirects"] = True
        elif token == "--compressed":
            continue
        elif token.startswith("-"):
            # consume the value if it looks like a long opt with a value
            if "=" not in token:
                next(iterator, None)
        else:
            if url is None:
                url = token

    if headers:
        task["headers"] = headers
    if data_parts:
        joined = "&".join(data_parts) if len(data_parts) > 1 else data_parts[0]
        is_json, parsed = _try_json_body(joined)
        if is_json:
            task["json"] = parsed
        else:
            task["data"] = joined

    if url:
        task["request_url"] = url

    return task


def curl_to_task(command: str) -> Dict[str, Any]:
    """
    Parse one cURL command into a LoadDensity HTTP task dict.
    """
    return _consume(_tokens(command))
