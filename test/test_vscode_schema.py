"""The VS Code extension's bundled schema must match ``action_json_schema()``.

``editors/vscode/schemas/loaddensity-action-schema.json`` is committed so the extension packages
without a Python step. Adding, renaming or removing an ``LD_*`` command changes the schema's
command enum; regenerate the file with
``python -c "from je_load_density import export_schema; export_schema('editors/vscode/schemas/loaddensity-action-schema.json')"``.
"""
import json
from pathlib import Path

from je_load_density.utils.schema.action_schema import action_json_schema

BUNDLED = Path(__file__).resolve().parents[1] / "editors" / "vscode" / "schemas" / "loaddensity-action-schema.json"


def test_bundled_vscode_schema_is_current():
    bundled = json.loads(BUNDLED.read_text(encoding="utf-8"))
    assert bundled == action_json_schema(), (  # nosec B101
        "editors/vscode/schemas/loaddensity-action-schema.json is stale; regenerate it with export_schema"
    )


def test_manifest_points_at_the_bundled_schema():
    manifest = json.loads((BUNDLED.parents[1] / "package.json").read_text(encoding="utf-8"))
    urls = [entry["url"] for entry in manifest["contributes"]["jsonValidation"]]
    assert "./schemas/loaddensity-action-schema.json" in urls  # nosec B101
