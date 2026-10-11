"""The wheels install ``je_load_density`` and nothing else.

With no ``include`` under ``[tool.setuptools.packages] find``, setuptools takes every directory that
has an ``__init__.py``, and ``test/`` is one: ``je_load_density`` 0.0.77 and ``je_load_density_dev``
0.0.80 installed this suite as a top-level ``test`` package (progress.md #24). Nothing is built
here. The patterns are read from the TOML and matched the way setuptools matches them, against the
packages in the checkout.
"""
from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterator

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: pytest depends on the tomli backport there
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "je_load_density"
METADATA_FILES = ["pyproject.toml", "dev.toml"]


def _find_settings(metadata: str) -> dict:
    """Return the ``find`` table of ``[tool.setuptools.packages]`` in a metadata file."""
    with (REPO_ROOT / metadata).open("rb") as handle:
        return tomllib.load(handle)["tool"]["setuptools"]["packages"]["find"]


def _packages(directory: Path, prefix: str = "") -> Iterator[str]:
    """Yield the dotted name of every regular package below ``directory``."""
    for child in sorted(directory.iterdir()):
        if child.is_dir() and (child / "__init__.py").is_file():
            name = f"{prefix}{child.name}"
            yield name
            yield from _packages(child, f"{name}.")


@pytest.mark.parametrize("metadata", METADATA_FILES)
def test_discovery_is_limited_to_the_package(metadata):
    assert _find_settings(metadata) == {"namespaces": False, "include": [PACKAGE, f"{PACKAGE}.*"]}


@pytest.mark.parametrize("metadata", METADATA_FILES)
def test_only_the_package_and_all_of_its_subpackages_are_selected(metadata):
    include = _find_settings(metadata)["include"]
    on_disk = set(_packages(REPO_ROOT))
    selected = {name for name in on_disk if any(fnmatchcase(name, pattern) for pattern in include)}
    assert PACKAGE in selected
    assert selected == {name for name in on_disk if name.split(".")[0] == PACKAGE}
