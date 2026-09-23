"""`dev.toml` builds `je_load_density_dev` from the same code as `pyproject.toml`.

It had kept only the `gui` extra, no console scripts and no `defusedxml`, so the dev package
installed without `loaddensity`, `loaddensity-mcp` or `loaddensity-lsp` (progress.md #6).
Everything but the name and the version has to match.
"""
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")  # stdlib from 3.11; CI also runs 3.10

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    with (REPO_ROOT / name).open("rb") as handle:
        return tomllib.load(handle)


STABLE = _load("pyproject.toml")
DEV = _load("dev.toml")


def test_names_differ():
    assert STABLE["project"]["name"] == "je_load_density"
    assert DEV["project"]["name"] == "je_load_density_dev"


@pytest.mark.parametrize("key", [
    "dependencies", "requires-python", "optional-dependencies", "scripts", "entry-points",
])
def test_project_tables_match(key):
    assert DEV["project"].get(key) == STABLE["project"].get(key)


def test_tool_settings_match():
    assert DEV.get("tool") == STABLE.get("tool")
