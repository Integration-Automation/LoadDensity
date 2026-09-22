"""Security floors in the optional-dependency extras, and packages kept out of them.

Each floor below clears an advisory whose vulnerable code LoadDensity can reach
(workspace item S-11, ``docs/updates`` U-20260923-01). Two packages must not come
back as extras: mitmproxy pins ``cryptography``, ``h2`` and ``msgpack`` below
their patched releases, and the ``mcp`` SDK's stdio transport never answers once
locust has gevent-patched ``threading`` (U-20260923-02).
"""
from pathlib import Path

import pytest
from packaging.requirements import Requirement

tomllib = pytest.importorskip("tomllib")

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _extras() -> dict:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["project"]["optional-dependencies"]


def _requirements(name: str):
    for extra, specs in _extras().items():
        for spec in specs:
            requirement = Requirement(spec)
            if requirement.name.lower() == name:
                yield extra, requirement


@pytest.mark.parametrize("name, vulnerable, patched", [
    ("kafka-python", "2.3.1", "2.3.2"),
    ("cryptography", "48.0.0", "48.0.1"),
])
def test_floor_excludes_the_vulnerable_release(name, vulnerable, patched):
    found = list(_requirements(name))
    assert found, f"{name} is no longer declared; drop it from this test"
    for extra, requirement in found:
        assert not requirement.specifier.contains(vulnerable), f"[{extra}] {requirement}"
        assert requirement.specifier.contains(patched), f"[{extra}] {requirement}"


@pytest.mark.parametrize("name", ["mitmproxy", "mcp"])
def test_no_extra_installs(name):
    assert not list(_requirements(name))
