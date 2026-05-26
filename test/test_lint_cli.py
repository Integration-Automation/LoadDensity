import json
from pathlib import Path

from je_load_density.tools.lint_files import main


def _write(tmp_path: Path, name: str, data) -> Path:
    target = tmp_path / name
    target.write_text(json.dumps(data), encoding="utf-8")
    return target


def test_lint_files_passes_for_known_actions(tmp_path):
    good = _write(tmp_path, "good.json", [["LD_summary"]])
    exit_code = main(["lint_files", str(good)])
    assert exit_code == 0


def test_lint_files_fails_for_unknown_commands(tmp_path):
    bad = _write(tmp_path, "bad.json", [["LD_typo", {}]])
    exit_code = main(["lint_files", str(bad)])
    assert exit_code == 1


def test_lint_files_ignores_missing_paths(tmp_path):
    exit_code = main(["lint_files", str(tmp_path / "missing.json")])
    assert exit_code == 0


def test_lint_files_handles_empty_arg_list():
    exit_code = main(["lint_files"])
    assert exit_code == 0
