"""
Action JSON formatter — canonical pretty-print for `*.json` action files.

Reads an action document, normalises whitespace + key order, writes it
back. Designed to be safe under pre-commit / CI.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Union

ActionDoc = Union[Dict[str, Any], List[Any]]


def _sort_task_keys(task: Dict[str, Any]) -> Dict[str, Any]:
    """Place semantically important keys (method/url/name) first."""
    primary = ("method", "request_url", "url", "name", "weight", "timeout")
    ordered: Dict[str, Any] = {}
    for key in primary:
        if key in task:
            ordered[key] = task[key]
    for key, value in task.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _normalise_action_list(actions: List[Any]) -> List[Any]:
    out: List[Any] = []
    for entry in actions:
        if isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], dict):
            kwargs = dict(entry[1])
            if "tasks" in kwargs and isinstance(kwargs["tasks"], list):
                kwargs["tasks"] = [
                    _sort_task_keys(task) if isinstance(task, dict) else task
                    for task in kwargs["tasks"]
                ]
            out.append([entry[0], kwargs])
        else:
            out.append(entry)
    return out


def format_action_document(doc: ActionDoc) -> ActionDoc:
    """Return a normalised copy of an action document."""
    if isinstance(doc, dict) and "load_density" in doc and isinstance(doc["load_density"], list):
        return {"load_density": _normalise_action_list(doc["load_density"])}
    if isinstance(doc, list):
        return _normalise_action_list(doc)
    return doc


def format_action_file(file_path: str, indent: int = 2) -> str:
    """Format an action JSON file in-place. Returns the rendered text."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(file_path)
    with open(path, "r", encoding="utf-8") as handle:
        doc = json.load(handle)
    formatted = format_action_document(doc)
    rendered = json.dumps(formatted, indent=indent, ensure_ascii=False) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    return rendered


def format_action_string(text: str, indent: int = 2) -> str:
    """Format an action JSON string. Returns the rendered text."""
    doc = json.loads(text)
    formatted = format_action_document(doc)
    return json.dumps(formatted, indent=indent, ensure_ascii=False) + "\n"
