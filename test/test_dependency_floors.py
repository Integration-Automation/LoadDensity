"""Security floors and caps in the optional-dependency extras.

Each floor below clears an advisory whose vulnerable code LoadDensity can reach;
the ``mcp`` cap keeps the 1.x server API that ``je_load_density/mcp_server`` is
written against. mitmproxy must not come back as an extra: it pins
``cryptography``, ``h2`` and ``msgpack`` below their patched releases (workspace
item S-11, ``docs/updates`` U-20260923-01).
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
    ("mcp", "1.28.0", "1.28.1"),
])
def test_floor_excludes_the_vulnerable_release(name, vulnerable, patched):
    found = list(_requirements(name))
    assert found, f"{name} is no longer declared; drop it from this test"
    for extra, requirement in found:
        assert not requirement.specifier.contains(vulnerable), f"[{extra}] {requirement}"
        assert requirement.specifier.contains(patched), f"[{extra}] {requirement}"


def test_mcp_stays_on_the_1x_api():
    for extra, requirement in _requirements("mcp"):
        assert not requirement.specifier.contains("2.0.0"), f"[{extra}] {requirement}"


def test_no_extra_installs_mitmproxy():
    assert not list(_requirements("mitmproxy"))
