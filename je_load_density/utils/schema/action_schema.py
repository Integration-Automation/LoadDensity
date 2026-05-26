"""
JSON Schema export for LoadDensity action JSON.

Produces a Draft 2020-12 schema describing the action list shape so
IDEs (VS Code, JetBrains) can offer completion and validation.
"""

import json as json_module
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

_SCHEMA_ID = "https://loaddensity.readthedocs.io/schema/action-1.0.json"
_DRAFT = "https://json-schema.org/draft/2020-12/schema"


def _known_ld_commands() -> Iterable[str]:
    from je_load_density.utils.executor.action_executor import executor
    return sorted(name for name in executor.event_dict if name.startswith("LD_"))


def _action_item_schema(known_commands: Iterable[str]) -> Dict[str, Any]:
    return {
        "type": "array",
        "minItems": 1,
        "maxItems": 2,
        "items": [
            {"type": "string", "enum": list(known_commands),
             "description": "Executor command name (LD_*)"},
            {"oneOf": [
                {"type": "object", "description": "Keyword arguments"},
                {"type": "array", "description": "Positional arguments"},
            ]},
        ],
    }


def action_json_schema(known_commands: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """
    Build the JSON Schema dict describing an action JSON document.
    """
    commands = list(known_commands) if known_commands is not None else list(_known_ld_commands())
    item = _action_item_schema(commands)
    action_list = {"type": "array", "items": item, "minItems": 1}
    return {
        "$schema": _DRAFT,
        "$id": _SCHEMA_ID,
        "title": "LoadDensity action JSON",
        "description": "Schema for LoadDensity action JSON files.",
        "oneOf": [
            action_list,
            {
                "type": "object",
                "properties": {"load_density": action_list},
                "required": ["load_density"],
                "additionalProperties": False,
            },
        ],
    }


def export_schema(path: str, known_commands: Optional[Iterable[str]] = None) -> str:
    """
    Write the schema to disk. Returns the absolute path written.
    """
    schema = action_json_schema(known_commands=known_commands)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json_module.dumps(schema, indent=2), encoding="utf-8")
    return str(out_path.resolve())
