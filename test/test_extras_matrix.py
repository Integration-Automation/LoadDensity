import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_matrix_module():
    specification = importlib.util.spec_from_file_location("extras_matrix", ROOT / "scripts/extras_matrix.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture
def metadata(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text('[project.optional-dependencies]\nredis = ["redis"]\ngui = ["PySide6"]\nall = []\n',
                    encoding="utf-8")
    return path


def test_pr_matrix_covers_each_extra_and_boundary_base_versions(metadata):
    cells = load_matrix_module().build_matrix(metadata)["include"]
    assert {(row["python"], row["extra"]) for row in cells} == {
        ("3.10", "base"), ("3.12", "base"), ("3.14", "base"),
        ("3.12", "redis"), ("3.12", "gui"), ("3.12", "all"),
    }


def test_schedule_matrix_covers_all_supported_versions(metadata):
    cells = load_matrix_module().build_matrix(metadata, scheduled=True)["include"]
    assert len(cells) == 20
    assert {row["python"] for row in cells} == {"3.10", "3.11", "3.12", "3.13", "3.14"}
    assert {row["extra"] for row in cells} == {"base", "redis", "gui", "all"}


def test_unsafe_extra_names_are_rejected_before_shell_parameters(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text('[project.optional-dependencies]\n"bad;echo x" = []\n', encoding="utf-8")
    with pytest.raises(ValueError, match="extra"):
        load_matrix_module().build_matrix(path)


def test_cli_writes_parseable_github_output(metadata, tmp_path):
    destination = tmp_path / "github-output"
    completed = subprocess.run([sys.executable, str(ROOT / "scripts/extras_matrix.py"),
                                "--metadata", str(metadata), "--output", str(destination)],
                               capture_output=True, text=True, timeout=10, check=False)
    assert completed.returncode == 0, completed.stderr
    key, value = destination.read_text(encoding="utf-8").strip().split("=", 1)
    assert key == "matrix"
    assert len(json.loads(value)["include"]) == 6
