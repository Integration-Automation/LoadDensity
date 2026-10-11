"""Contract test for the legacy CLI flags that other repositories call.

PyBreeze starts ``python -m je_load_density --execute_str <json>`` (JSON-encoded a second
time on Windows, see ``pybreeze/extend/process_executor/python_task_process_manager.py``)
and ``--execute_file <path>``; TestPioneer's ``parallel_run`` starts
``--execute_file <path>``; PyBreeze's "create project" menu calls
``je_load_density.create_project_dir()`` in process. Nothing on the consumer side tests
these, so this file does: renaming or removing a flag, or dropping the second
JSON decode on Windows, breaks them (workspace item X-7).
"""
import json
import os
import subprocess  # nosec B404 - the CLI is exercised as a real child process
import sys
from pathlib import Path

import pytest

import je_load_density

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "je_load_density"
IS_WINDOWS = sys.platform in ("win32", "cygwin", "msys")


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Run ``python -m PACKAGE`` from this checkout; *cwd* catches any log file it writes."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPO_ROOT), env.get("PYTHONPATH")]))
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(  # nosec B603  # nosemgrep - fixed argument list, no shell
        [sys.executable, "-m", PACKAGE, *args],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
        timeout=300, check=False,
    )


def _pybreeze_execute_str(actions: list) -> str:
    """Encode *actions* the way PyBreeze's ``start_test_process`` does."""
    payload = json.dumps(actions)
    return json.dumps(payload) if IS_WINDOWS else payload


MARKER = "legacy-cli-contract-marker"


def _actions(_target: Path) -> list:
    """A harmless action list whose only effect is printing MARKER."""
    return [["print", [MARKER]]]


def _assert_ran(result: subprocess.CompletedProcess, _target: Path) -> None:
    assert result.returncode == 0, result.stderr
    assert MARKER in result.stdout, result.stdout + result.stderr


@pytest.mark.parametrize("flag", ["-e", "--execute_file"])
def test_execute_file(tmp_path, flag):
    target = tmp_path / "out"
    action_file = tmp_path / "actions.json"
    action_file.write_text(json.dumps(_actions(target)), encoding="utf-8")
    _assert_ran(_run_cli(tmp_path, flag, str(action_file)), target)


@pytest.mark.parametrize("flag", ["-d", "--execute_dir"])
def test_execute_dir(tmp_path, flag):
    target = tmp_path / "out"
    action_dir = tmp_path / "actions"
    action_dir.mkdir()
    (action_dir / "actions.json").write_text(json.dumps(_actions(target)), encoding="utf-8")
    _assert_ran(_run_cli(tmp_path, flag, str(action_dir)), target)


def test_execute_str_as_pybreeze_sends_it(tmp_path):
    target = tmp_path / "out"
    _assert_ran(_run_cli(tmp_path, "--execute_str", _pybreeze_execute_str(_actions(target))), target)


@pytest.mark.parametrize("flag", ["-c", "--create_project"])
def test_create_project(tmp_path, flag):
    project = tmp_path / "project"
    result = _run_cli(tmp_path, flag, str(project))
    assert result.returncode == 0, result.stderr
    assert project.is_dir(), result.stdout + result.stderr
    assert any(project.rglob("*.json")), result.stdout + result.stderr


def test_no_flag_exits_non_zero(tmp_path):
    assert _run_cli(tmp_path).returncode != 0


def test_create_project_dir_is_exported():
    assert callable(je_load_density.create_project_dir)


def test_cli_executes_with_reporter_api_without_core_collector(monkeypatch):
    from types import SimpleNamespace

    from je_action_core.reporting import PrintReporter

    from je_load_density import __main__ as cli
    from je_load_density.utils.exception.exceptions import LoadDensityTestExecuteException
    from je_load_density.utils.executor.action_executor import Executor

    settings = Executor().settings
    settings_before = settings
    reported = []
    monkeypatch.setattr(PrintReporter, "on_failure", lambda *args: reported.append("failure"))
    monkeypatch.setattr(PrintReporter, "on_records", lambda *args: reported.append("records"))

    def execute(actions):
        assert actions == [["failing action", []]]
        legacy.settings.reporter.on_failure(actions[0], RuntimeError("failed"))
        legacy.settings.reporter.on_records({"failure": "failed"})

    legacy = SimpleNamespace(settings=settings, execute_action=execute)
    monkeypatch.setattr(cli, "executor", legacy)
    with pytest.raises(LoadDensityTestExecuteException, match="1 action"):
        cli._execute_cli_actions([["failing action", []]])
    assert legacy.settings is settings_before
    assert reported == ["failure", "records"]
