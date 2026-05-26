"""
JMeter JMX importer.

Walks an XML JMeter test plan and emits one LoadDensity HTTP task per
``HTTPSamplerProxy`` element, including headers (from sibling
``HeaderManager`` elements) and request bodies.

Only the HTTP sampler subset is handled — JDBC, JMS, etc. samplers are
ignored.
"""

from typing import Any, Dict, List, Optional

import defusedxml.ElementTree as _ET  # type: ignore


_SAMPLER_TAG = "HTTPSamplerProxy"
_HEADER_MANAGER_TAG = "HeaderManager"
_STRING_PROP = "stringProp"
_BOOL_PROP = "boolProp"
_ELEMENT_PROP = "elementProp"
_COLLECTION_PROP = "collectionProp"


def load_jmeter_jmx(file_path: str) -> Any:
    with open(file_path, "r", encoding="utf-8") as fh:
        return _ET.fromstring(fh.read())


def _string_prop(element, name: str, default: str = "") -> str:
    for prop in element.findall(_STRING_PROP):
        if prop.get("name") == name:
            return prop.text or default
    return default


def _bool_prop(element, name: str, default: bool = False) -> bool:
    for prop in element.findall(_BOOL_PROP):
        if prop.get("name") == name:
            return (prop.text or "").strip().lower() == "true"
    return default


def _url_from_sampler(sampler) -> str:
    protocol = _string_prop(sampler, "HTTPSampler.protocol") or "http"
    host = _string_prop(sampler, "HTTPSampler.domain")
    port = _string_prop(sampler, "HTTPSampler.port")
    path = _string_prop(sampler, "HTTPSampler.path") or "/"
    if not host:
        return path
    authority = host if not port else f"{host}:{port}"
    if not path.startswith("/"):
        path = "/" + path
    return f"{protocol}://{authority}{path}"


def _headers_from_manager(manager) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    collection = manager.find(f"{_COLLECTION_PROP}[@name='HeaderManager.headers']")
    if collection is None:
        return headers
    for element in collection.findall(_ELEMENT_PROP):
        name = _string_prop(element, "Header.name")
        value = _string_prop(element, "Header.value")
        if name:
            headers[name] = value
    return headers


def _body_from_arguments(sampler) -> Optional[Any]:
    arguments = sampler.find(
        f"{_ELEMENT_PROP}[@name='HTTPsampler.Arguments']"
    )
    if arguments is None:
        return None
    collection = arguments.find(
        f"{_COLLECTION_PROP}[@name='Arguments.arguments']"
    )
    if collection is None:
        return None

    raw_arguments: List[Dict[str, str]] = []
    for element in collection.findall(_ELEMENT_PROP):
        raw_arguments.append({
            "name": _string_prop(element, "Argument.name"),
            "value": _string_prop(element, "Argument.value"),
        })
    if not raw_arguments:
        return None
    only = raw_arguments[0]
    if not only["name"]:
        return only["value"]
    return {arg["name"]: arg["value"] for arg in raw_arguments}


def _sampler_to_task(sampler, sibling_headers: Dict[str, str]) -> Dict[str, Any]:
    task: Dict[str, Any] = {
        "method": (_string_prop(sampler, "HTTPSampler.method") or "GET").lower(),
        "request_url": _url_from_sampler(sampler),
        "name": sampler.get("testname") or "JMeter sample",
    }
    if sibling_headers:
        task["headers"] = dict(sibling_headers)
    body = _body_from_arguments(sampler)
    if body is not None:
        task["data"] = body
    return task


def _build_parent_map(root) -> Dict[Any, Any]:
    return {child: parent for parent in root.iter() for child in parent}


def _collect_ancestor_headers(node, parent_map: Dict[Any, Any]) -> Dict[str, str]:
    """
    Walk up the tree from ``node``; at each level collect every sibling
    HeaderManager that appears before the node. Outer scopes are merged
    first so inner overrides win.
    """
    levels: List[Dict[str, str]] = []
    cursor = node
    while cursor in parent_map:
        parent = parent_map[cursor]
        siblings = list(parent)
        try:
            cursor_index = siblings.index(cursor)
        except ValueError:
            cursor_index = len(siblings)
        level: Dict[str, str] = {}
        for sibling in siblings[:cursor_index]:
            if sibling.tag == _HEADER_MANAGER_TAG:
                level.update(_headers_from_manager(sibling))
        if level:
            levels.append(level)
        cursor = parent

    merged: Dict[str, str] = {}
    for level in reversed(levels):
        merged.update(level)
    return merged


def jmeter_to_tasks(root) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    parent_map = _build_parent_map(root)
    for sampler in root.iter(_SAMPLER_TAG):
        headers = _collect_ancestor_headers(sampler, parent_map)
        out.append(_sampler_to_task(sampler, headers))
    return out


def jmeter_to_action_json(
    root,
    user: str = "fast_http_user",
    user_count: int = 10,
    spawn_rate: int = 5,
    test_time: int = 60,
) -> Dict[str, Any]:
    tasks = jmeter_to_tasks(root)
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
