"""The source distribution carries no tests.

setuptools adds ``test*/test*.py`` to an sdist by default, so ``je_load_density_dev`` 0.0.81 still
shipped 72 files of this suite after the wheels had stopped installing it
(``test/test_wheel_packages.py``). ``MANIFEST.in`` prunes the directory. Nothing is built here:
the template is read and its commands are checked in the order setuptools applies them.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DIRECTORY = Path(__file__).resolve().parent.name
PRUNE = ["prune", TEST_DIRECTORY]
# The template commands that add files; one of them after the prune could bring tests back.
ADDING = {"include", "recursive-include", "global-include", "graft"}


def _commands() -> list[list[str]]:
    """Return the commands of ``MANIFEST.in`` in order, each split into words."""
    lines = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
    return [line.split() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def test_manifest_prunes_the_test_directory():
    assert PRUNE in _commands()


def test_nothing_after_the_prune_adds_files_back():
    commands = _commands()
    following = commands[commands.index(PRUNE) + 1:]
    assert [command for command in following if command[0] in ADDING] == []
