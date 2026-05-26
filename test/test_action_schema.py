import json
from pathlib import Path

from je_load_density.utils.schema.action_schema import (
    action_json_schema,
    export_schema,
)


def test_action_json_schema_has_id_and_draft():
    schema = action_json_schema(known_commands=["LD_start_test"])
    assert schema["$schema"].startswith("https://json-schema.org/draft/")
    assert schema["$id"].endswith(".json")
    assert "LoadDensity" in schema["title"]


def test_action_json_schema_enumerates_known_commands():
    schema = action_json_schema(known_commands=["LD_start_test", "LD_summary"])
    item_schema = schema["oneOf"][0]["items"]
    enum = item_schema["items"][0]["enum"]
    assert enum == ["LD_start_test", "LD_summary"]


def test_action_json_schema_accepts_both_top_level_shapes():
    schema = action_json_schema(known_commands=["LD_summary"])
    shapes = schema["oneOf"]
    assert shapes[0]["type"] == "array"
    assert shapes[1]["type"] == "object"
    assert shapes[1]["required"] == ["load_density"]


def test_export_schema_writes_json_file(tmp_path):
    out_file = tmp_path / "schema.json"
    written = export_schema(str(out_file), known_commands=["LD_start_test"])
    assert Path(written).exists()
    parsed = json.loads(Path(written).read_text(encoding="utf-8"))
    assert parsed["title"] == "LoadDensity action JSON"
