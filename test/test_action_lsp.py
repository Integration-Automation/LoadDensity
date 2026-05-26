import json

from je_load_density.action_lsp.server import (
    ActionLspServer,
    completion_items,
    compute_diagnostics,
)


def test_compute_diagnostics_empty_document():
    assert compute_diagnostics("") == []


def test_compute_diagnostics_invalid_json():
    diagnostics = compute_diagnostics("{not json")
    assert diagnostics
    assert diagnostics[0]["severity"] == 1
    assert "invalid JSON" in diagnostics[0]["message"]


def test_compute_diagnostics_lints_known_actions():
    document = json.dumps({"load_density": [
        ["LD_bogus_command", {}],
    ]})
    diagnostics = compute_diagnostics(document)
    assert diagnostics
    assert "unknown-command" in diagnostics[0]["message"]


def test_completion_items_include_ld_commands():
    known, items = completion_items()
    assert "LD_start_test" in known
    labels = {item["label"] for item in items}
    assert "LD_start_test" in labels
    assert "LD_lint_action" in labels


def test_initialize_returns_capabilities():
    server = ActionLspServer()
    result = server._on_initialize({})
    assert result["capabilities"]["textDocumentSync"] == 1
    assert "completionProvider" in result["capabilities"]
    assert result["serverInfo"]["name"] == "loaddensity-action-lsp"
