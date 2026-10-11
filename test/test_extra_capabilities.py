import importlib
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def probes(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "test/smoke"))
    return importlib.import_module("capability_probe")


def test_every_declared_extra_has_a_non_skipping_probe(monkeypatch):
    with (ROOT / "pyproject.toml").open("rb") as handle:
        extras = tomllib.load(handle)["project"]["optional-dependencies"]
    assert set(probes(monkeypatch).PROBES) == set(extras) - {"all"}


def test_unknown_extra_is_an_error(monkeypatch):
    probe_module = probes(monkeypatch)
    with pytest.raises(ValueError, match="extra"):
        probe_module.run_probe("unregistered")


def test_missing_declared_capability_is_a_failure(monkeypatch):
    import builtins

    probe_module = probes(monkeypatch)
    original = builtins.__import__

    def missing_redis(name, *args, **kwargs):
        if name == "redis":
            raise ImportError("declared redis dependency missing")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_redis)
    with pytest.raises(ImportError, match="redis"):
        probe_module.run_probe("redis")


def test_all_probe_reports_failures_and_still_exercises_other_capabilities(monkeypatch):
    import subprocess

    probe_module = probes(monkeypatch)
    calls = []
    local_calls = []

    def broken():
        raise ImportError("missing dependency")

    def child(arguments, **options):
        calls.append(arguments[-1])
        assert options["check"] is True
        assert options["timeout"] > 0
        if arguments[-1] == "broken":
            raise subprocess.CalledProcessError(1, arguments)

    monkeypatch.setattr(probe_module, "PROBES", {"broken": broken, "healthy": lambda: local_calls.append("healthy")})
    monkeypatch.setattr(subprocess, "run", child)
    with pytest.raises(RuntimeError, match="broken"):
        probe_module.run_probe("all")
    assert calls == ["broken", "healthy"]
    assert local_calls == []
