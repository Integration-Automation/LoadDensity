"""
Action JSON linter.

Statically checks a LoadDensity action JSON for unknown commands,
hard-coded URLs, weak parameter usage, missing tasks, and a few other
foot-guns. Returns a list of ``LintFinding`` records — does not raise
unless the input is structurally invalid.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union

from je_load_density.utils.json.json_file.json_file import read_action_json

_HARDCODED_URL = re.compile(r"^https?://", re.IGNORECASE)
_PLACEHOLDER = re.compile(r"\$\{[^}]+\}")
_MAX_BODY_BYTES = 1024 * 1024  # 1 MiB


@dataclass
class LintFinding:
    """One rule hit. ``severity`` is ``error`` or ``warning``."""

    rule: str
    severity: str
    message: str
    location: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class _Context:
    known_commands: Set[str]
    findings: List[LintFinding] = field(default_factory=list)

    def add(self, rule: str, severity: str, message: str, location: str = "") -> None:
        self.findings.append(LintFinding(rule, severity, message, location))


def _known_commands() -> Set[str]:
    from je_load_density.utils.executor.action_executor import executor
    return {name for name in executor.event_dict if name.startswith("LD_")}


def _unwrap(actions: Union[List[Any], Dict[str, Any]]) -> List[Any]:
    if isinstance(actions, dict):
        return actions.get("load_density") or []
    return actions or []


def _check_command_name(ctx: _Context, name: str, where: str) -> None:
    if not name.startswith("LD_"):
        return
    if name not in ctx.known_commands:
        ctx.add("unknown-command", "error",
                f"unknown command {name!r}; check spelling or register it via add_command_to_executor",
                where)


def _check_url(ctx: _Context, value: str, where: str) -> None:
    if not isinstance(value, str):
        return
    if _HARDCODED_URL.match(value) and not _PLACEHOLDER.search(value):
        ctx.add("hardcoded-url", "warning",
                f"hard-coded URL {value!r}; consider ${{var.base}} placeholder",
                where)


def _check_task(ctx: _Context, task: Dict[str, Any], where: str) -> None:
    url = task.get("request_url") or task.get("url")
    if url is not None:
        _check_url(ctx, url, f"{where}.request_url")

    body = task.get("data") or task.get("json")
    if isinstance(body, (bytes, str)) and len(body) > _MAX_BODY_BYTES:
        ctx.add("oversize-body", "warning",
                f"task body is {len(body)} bytes; consider streaming or a smaller fixture",
                where)


def _check_start_test_payload(ctx: _Context, payload: Dict[str, Any], where: str) -> None:
    tasks = payload.get("tasks")
    if tasks is None:
        ctx.add("missing-tasks", "error",
                "LD_start_test missing 'tasks' key", where)
        return

    if isinstance(tasks, dict) and "tasks" in tasks:
        task_list = tasks.get("tasks")
    else:
        task_list = tasks

    if isinstance(task_list, list):
        for index, task in enumerate(task_list):
            if isinstance(task, dict):
                _check_task(ctx, task, f"{where}.tasks[{index}]")
    elif isinstance(task_list, dict):
        for method, task in task_list.items():
            if isinstance(task, dict):
                _check_task(ctx, task, f"{where}.tasks.{method}")


def _check_action(ctx: _Context, action: Any, index: int) -> None:
    where = f"actions[{index}]"
    if not isinstance(action, list) or not action:
        ctx.add("invalid-shape", "error",
                "action must be a non-empty list", where)
        return

    name = action[0]
    if not isinstance(name, str):
        ctx.add("invalid-shape", "error",
                "action name must be a string", where)
        return

    _check_command_name(ctx, name, where)

    if name == "LD_start_test" and len(action) >= 2 and isinstance(action[1], dict):
        _check_start_test_payload(ctx, action[1], where)


def lint_action(actions: Union[List[Any], Dict[str, Any]],
                known_commands: Optional[Set[str]] = None) -> List[Dict[str, str]]:
    """
    Lint an action JSON. Returns a list of finding dicts.
    """
    ctx = _Context(known_commands=known_commands or _known_commands())
    body = _unwrap(actions)
    if not isinstance(body, list):
        ctx.add("invalid-shape", "error",
                "top-level action document must be a list or {'load_density': [...]}", "")
        return [f.as_dict() for f in ctx.findings]

    for index, action in enumerate(body):
        _check_action(ctx, action, index)
    return [f.as_dict() for f in ctx.findings]


def lint_action_file(path: str,
                     known_commands: Optional[Set[str]] = None) -> List[Dict[str, str]]:
    """
    Read an action JSON file from disk and lint it.
    """
    return lint_action(read_action_json(path), known_commands=known_commands)
