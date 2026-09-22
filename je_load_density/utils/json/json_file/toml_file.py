"""
TOML action-document loader (Python 3.11+ stdlib tomllib for read).

For writing, a minimal stdlib-based encoder is used to keep dependencies
tight. Tomllib does not write; we serialise via a small inline encoder
limited to the simple types LoadDensity action documents use.
"""

import tomllib
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Union

from je_load_density.utils.exception.exceptions import LoadDensityTestJsonException
from je_load_density.utils.exception.exception_tags import (
    cant_find_json_error,
    cant_save_json_error,
)

_toml_file_lock = Lock()


def read_action_toml(toml_file_path: str) -> Union[Dict[str, Any], list]:
    """Read a TOML action document. Returns the parsed dictionary."""
    try:
        with _toml_file_lock:
            file_path = Path(toml_file_path)
            if not (file_path.exists() and file_path.is_file()):
                raise LoadDensityTestJsonException(cant_find_json_error)
            with open(toml_file_path, "rb") as read_file:
                return tomllib.load(read_file)
    except LoadDensityTestJsonException:
        raise
    except Exception as error:
        raise LoadDensityTestJsonException(f"{cant_find_json_error}: {error}") from error


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise TypeError(f"unsupported TOML scalar type: {type(value).__name__}")


def _format_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    if isinstance(value, dict):
        body = ", ".join(f"{k} = {_format_value(v)}" for k, v in value.items())
        return "{" + body + "}"
    return _format_scalar(value)


def write_action_toml(toml_save_path: str, action_doc: Dict[str, Any]) -> None:
    """
    Write a top-level dict as TOML.

    Restricted to dict-of-scalars/lists/sub-dicts because the LoadDensity
    action surface never needs anything richer.
    """
    if not isinstance(action_doc, dict):
        raise TypeError("TOML root must be a dict")
    lines = []
    for key, value in action_doc.items():
        lines.append(f"{key} = {_format_value(value)}")
    try:
        with _toml_file_lock:
            with open(toml_save_path, "w+", encoding="utf-8") as file_to_write:
                file_to_write.write("\n".join(lines) + "\n")
    except Exception as error:
        raise LoadDensityTestJsonException(f"{cant_save_json_error}: {error}") from error
