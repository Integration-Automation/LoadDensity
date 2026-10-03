"""Capability validation for the native HTTP engine, performed before I/O."""

import math
import ssl
from collections.abc import Mapping
from typing import Any

from je_load_density.utils.load_shapes.shapes import _soak_tick, _spike_tick, _stages_tick
from je_load_density.wrapper.user_template.scenario_runner import _coerce_tasks_payload

_TASK_FIELDS = frozenset(
    {
        "method",
        "request_url",
        "url",
        "name",
        "params",
        "headers",
        "cookies",
        "json",
        "data",
        "timeout",
        "allow_redirects",
        "verify",
        "files",
        "cert",
        "client_cert",
        "auth",
        "proxy",
        "assertions",
        "extract",
        "weight",
        "run_if",
        "skip_if",
        "retry",
        "think_time",
        "throttle",
        "step_id",
        "scenario_id",
    }
)
_ASSERTIONS = frozenset({"status_code", "contains", "not_contains", "json_path", "header"})
_EXTRACTORS = frozenset({"json_path", "header", "status_code"})
_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "trace", "connect"})
_RETRY_FIELDS = {
    "transient": 5,
    "flaky": 2,
    "permanent": 0,
    "base_delay": 0.1,
    "max_delay": 5,
    "backoff_factor": 2,
    "jitter": 0.25,
}


def _condition(expression: Any) -> None:
    if expression is None:
        return
    if isinstance(expression, (str, bool, int)):
        return
    if not isinstance(expression, dict) or len(expression) != 1:
        raise ValueError("Conditions require one supported operator")
    operator, arguments = next(iter(expression.items()))
    if operator == "truthy":
        return
    if operator not in {"equals", "not_equals", "in"}:
        raise ValueError("Unsupported condition operator")
    if not isinstance(arguments, list) or len(arguments) != 2:
        raise ValueError("Condition operator requires two arguments")


def _request_types(task: dict) -> None:
    accepted = {
        "headers": (Mapping, list, tuple),
        "params": (Mapping, list, tuple, str, bytes),
        "cookies": (Mapping,),
        "data": (Mapping, str, bytes),
        "files": (Mapping, list, tuple),
        "allow_redirects": (bool,),
        "verify": (bool, str, ssl.SSLContext),
        "proxy": (str,),
        "cert": (str, list, tuple),
        "client_cert": (str, list, tuple),
        "name": (str,),
    }
    for key, types in accepted.items():
        value = task.get(key)
        if value is not None and not isinstance(value, types):
            raise ValueError(f"Invalid native request field {key}")
    for key in ("run_if", "skip_if"):
        if key in task:
            _condition(task[key])
    if isinstance(task.get("verify"), ssl.SSLContext) and ("cert" in task or "client_cert" in task):
        raise ValueError("Configure the certificate on your SSLContext and omit cert/client_cert")


def number(value: Any, name: str, *, integer: bool = False, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    if integer and int(value) != value:
        raise ValueError(f"{name} must be an integer")
    return value


def _validate_rules(task: dict) -> None:
    _validate_assertions(task.get("assertions") or [])
    _validate_extractors(task.get("extract") or [])


def _validate_assertions(rules: list) -> None:
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("type") not in _ASSERTIONS:
            raise ValueError("Unsupported native assertion")
        _rule_fields(rule, {"type", "value", "path", "name"})
        if "value" not in rule:
            raise ValueError("Assertions require value")
        if rule["type"] == "status_code":
            number(rule.get("value"), "assertion status_code", integer=True, minimum=100)


def _validate_extractors(rules: list) -> None:
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("from", "json_path") not in _EXTRACTORS:
            raise ValueError("Unsupported native extractor")
        _rule_fields(rule, {"from", "var", "scope", "path", "name"})
        if not rule.get("var") or rule.get("scope", "var") not in {"var", "session"}:
            raise ValueError("Extractors require var and scope var/session")


def _rule_fields(rule: dict, fields: set) -> None:
    if set(rule) - fields:
        raise ValueError("Unsupported assertion/extractor configuration")
    for key in ("path", "name", "var"):
        if key in rule and not isinstance(rule[key], str):
            raise ValueError(f"Rule {key} must be a string")


def _validate_timing(task: dict) -> None:
    _validate_retry(task.get("retry"))
    _validate_think_time(task.get("think_time", 0))
    _validate_throttle(task.get("throttle"))


def _validate_retry(retry: Any) -> None:
    if retry is not None:
        if not isinstance(retry, dict) or set(retry) - _RETRY_FIELDS.keys():
            raise ValueError("Unsupported retry configuration")
        for key, value in retry.items():
            number(value, f"retry.{key}", integer=key in {"transient", "flaky", "permanent"})


def _validate_think_time(think: Any) -> None:
    if isinstance(think, dict):
        if set(think) - {"min", "max"}:
            raise ValueError("Unsupported think_time configuration")
        number(think.get("min", 0), "think_time.min")
        number(think.get("max", think.get("min", 0)), "think_time.max")
    else:
        number(think, "think_time")


def _validate_throttle(throttle: Any) -> None:
    if throttle is not None:
        if not isinstance(throttle, dict) or set(throttle) - {"key", "rps", "burst"}:
            raise ValueError("Unsupported throttle configuration")
        number(throttle.get("rps"), "throttle.rps", minimum=0.000001)
        if "burst" in throttle:
            number(throttle["burst"], "throttle.burst", integer=True, minimum=1)


def validate_tasks(raw_tasks: Any) -> dict:
    if not isinstance(raw_tasks, (list, dict)):
        raise ValueError("tasks must be a list or scenario mapping")
    if isinstance(raw_tasks, dict) and "tasks" in raw_tasks:
        if set(raw_tasks) - {"mode", "tasks"}:
            raise ValueError("Unsupported scenario configuration")
        _validate_task_items(raw_tasks["tasks"])
    else:
        _validate_task_items(raw_tasks)
    payload = _coerce_tasks_payload(raw_tasks)
    if payload["mode"] not in {"sequence", "weighted", "conditional"}:
        raise ValueError("Native scenarios support sequence, weighted and conditional")
    if not payload["tasks"]:
        raise ValueError("At least one HTTP task is required")
    for task in payload["tasks"]:
        _validate_task(task)
    return payload


def _validate_task_items(raw: Any) -> None:
    if isinstance(raw, list) and raw and all(isinstance(item, dict) for item in raw):
        return
    if isinstance(raw, dict) and raw and all(isinstance(item, dict) for item in raw.values()):
        return
    raise ValueError("Every task must be a mapping")


def _validate_task(task: dict) -> None:
    unknown = set(task) - _TASK_FIELDS
    if unknown:
        raise ValueError(f"Unsupported native task fields: {sorted(unknown)}")
    if str(task.get("method", "get")).lower() not in _METHODS:
        raise ValueError("Unsupported HTTP method")
    url = task.get("request_url") or task.get("url")
    if not isinstance(url, str) or not url:
        raise ValueError("HTTP task requires request_url")
    if "${" not in url and not url.startswith(("http://", "https://", "/")):
        raise ValueError("Only HTTP(S) URLs are supported")
    if "timeout" in task and "${" not in str(task["timeout"]):
        number(task["timeout"], "timeout", minimum=0.000001)
    _validate_auth(task.get("auth"))
    _request_types(task)
    number(task.get("weight", 1), "weight", integer=True)
    _validate_rules(task)
    _validate_timing(task)


def _validate_auth(auth: Any) -> None:
    if auth is not None and (not isinstance(auth, dict) or auth.get("type") not in {"basic", "bearer"}):
        raise ValueError("Native auth supports basic and bearer")
    if auth is not None:
        names = {"type", "username", "password"} if auth["type"] == "basic" else {"type", "token"}
        if set(auth) - names:
            raise ValueError("Unsupported auth configuration")


def validate_shape(name: str | None, config: dict | None) -> None:
    if name is None:
        return
    config = config or {}
    if not isinstance(config, dict):
        raise ValueError("Shape configuration must be a mapping")
    if name not in {"stages", "spike", "soak"}:
        raise ValueError("Unsupported native load shape")
    fields = {
        "stages": {"stages"},
        "spike": {"baseline_users", "spike_users", "spawn_rate", "pre_seconds", "spike_seconds", "post_seconds"},
        "soak": {"users", "spawn_rate", "ramp_seconds", "hold_seconds", "cooldown_seconds"},
    }
    if set(config) - fields[name]:
        raise ValueError("Unsupported shape configuration")
    entries = config.get("stages", []) if name == "stages" else [config]
    if not entries:
        raise ValueError("Stages shape requires stages")
    for stage in entries:
        _validate_stage(stage, name)


def _validate_stage(stage: Any, name: str) -> None:
    if not isinstance(stage, dict):
        raise ValueError("Shape stages must be mappings")
    if name == "stages" and set(stage) - {"duration", "users", "spawn_rate"}:
        raise ValueError("Unsupported stage configuration")
    for key, value in stage.items():
        number(value, f"shape.{key}", integer=key.endswith("users") or key == "spawn_rate")
    if stage.get("spawn_rate", 1) <= 0:
        raise ValueError("Shape spawn_rate must be positive")


def shape_target(name: str | None, config: dict, elapsed: float, users: int, spawn_rate: float):
    if name == "stages":
        return _stages_tick(config["stages"], elapsed)
    if name == "spike":
        return _spike_tick(config, elapsed)
    if name == "soak":
        return _soak_tick(config, elapsed)
    return users, spawn_rate
