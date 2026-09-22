"""
YAML action-document loader. Lazy-imports ``pyyaml``.
"""

from pathlib import Path
from threading import Lock
from typing import Union

from je_load_density.utils.exception.exceptions import LoadDensityTestJsonException
from je_load_density.utils.exception.exception_tags import (
    cant_find_json_error,
    cant_save_json_error,
)

_yaml_file_lock = Lock()


def _import_yaml():
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError(
            "pyyaml is required for YAML action documents; install with: pip install pyyaml"
        ) from error
    return yaml


def read_action_yaml(yaml_file_path: str) -> Union[dict, list]:
    """Read a YAML action document and return its parsed contents."""
    try:
        yaml = _import_yaml()
        with _yaml_file_lock:
            file_path = Path(yaml_file_path)
            if not (file_path.exists() and file_path.is_file()):
                raise LoadDensityTestJsonException(cant_find_json_error)
            with open(yaml_file_path, "r", encoding="utf-8") as read_file:
                return yaml.safe_load(read_file)
    except LoadDensityTestJsonException:
        raise
    except Exception as error:
        raise LoadDensityTestJsonException(f"{cant_find_json_error}: {error}") from error


def write_action_yaml(yaml_save_path: str, action_doc: Union[dict, list]) -> None:
    """Write an action document to disk as YAML."""
    try:
        yaml = _import_yaml()
        with _yaml_file_lock:
            with open(yaml_save_path, "w+", encoding="utf-8") as file_to_write:
                yaml.safe_dump(action_doc, file_to_write, allow_unicode=True, sort_keys=False)
    except Exception as error:
        raise LoadDensityTestJsonException(f"{cant_save_json_error}: {error}") from error
