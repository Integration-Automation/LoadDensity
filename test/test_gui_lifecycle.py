"""Desktop lifecycle contracts without starting external services."""

import io
import json
import os
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


class ControlledWorker(QObject):
    state_changed = Signal(str)
    snapshot_ready = Signal(dict)
    log_message = Signal(str)
    completed = Signal(dict)

    def __init__(self, **kwargs):
        super().__init__()
        self.config = kwargs
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def isRunning(self):
        return self.started

    def request_stop(self):
        self.stopped = True

    def shutdown(self, timeout_ms=6000):
        self.stopped = True
        self.started = False
        return True


@pytest.fixture
def widget(application, monkeypatch):
    from je_load_density.gui import main_widget

    monkeypatch.setattr(main_widget, "LoadDensityGUIThread", ControlledWorker)
    view = main_widget.LoadDensityWidget()
    view.url_input.setText("http://127.0.0.1:8080/")
    view.test_time_input.setText("1")
    view.user_count_input.setText("2")
    view.spawn_rate_input.setText("2")
    yield view
    view.close()


def test_parent_import_does_not_patch_native_threads():
    source = "import sys; import je_load_density.gui.main_widget; assert 'locust' not in sys.modules"
    result = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_duplicate_start_and_visible_stop(widget):
    widget.run_load_density()
    worker = widget.run_load_density_thread
    widget.run_load_density()
    assert widget.run_load_density_thread is worker
    assert widget.run_state == "running"
    assert not widget.start_button.isEnabled()
    widget.stop_load_density()
    assert widget.run_state == "stopping"
    assert worker.stopped


def test_new_run_clears_previous_summary(widget):
    widget.last_summary = {"requests": 10}
    widget.run_load_density()
    assert widget.last_summary == {}


def test_embedded_widget_has_readable_dark_palette(widget, application):
    from PySide6.QtGui import QPalette

    widget.resize(1200, 850)
    widget.show()
    application.processEvents()
    foreground = widget.url_input.palette().color(QPalette.Text)
    background = widget.url_input.palette().color(QPalette.Base)
    assert foreground.lightnessF() > 0.8
    assert background.lightnessF() < 0.25
    assert widget.chart_panel._rps_view.height() >= 210
    assert "p50" in widget.stats_panel.latency_label.text()
    assert "p99" in widget.stats_panel.latency_label.text()


def test_failure_keeps_results_and_close_stops_worker(widget):
    widget.run_load_density()
    worker = widget.run_load_density_thread
    snapshot = {"summary": {"requests": 12, "failures": 2, "p95_ms": 40},
                "records": [{"name": "<b>request</b>", "response_time_ms": 40, "failed": False}]}
    worker.snapshot_ready.emit(snapshot)
    worker.completed.emit({"state": "failed", "summary": snapshot["summary"]})
    assert widget.run_state == "failed"
    assert widget.results_table.rowCount() == 1
    assert widget.results_table.item(0, 0).text() == "<b>request</b>"
    assert "12" in widget.stats_panel.totals_label.text()
    widget.close()
    assert worker.stopped


def test_protocol_bounds_and_redacts_records():
    from je_load_density.gui.run_protocol import make_snapshot

    records = [{"test_url": "https://user:password@example.org/a?token=secret", "start_time": 10,
                "response_time_ms": 20, "request_headers": {"Authorization": "secret"}}] * 250
    snapshot = make_snapshot(records, [], users=2, elapsed=1)
    assert snapshot["summary"]["requests"] == 250
    assert len(snapshot["records"]) == 200
    assert snapshot["summary"]["p95_ms"] == 20
    serialized = str(snapshot)
    assert "secret" not in serialized
    assert "password" not in serialized
    assert "Authorization" not in serialized


@pytest.mark.parametrize("value, expected", [
    ("/api?token=super-secret#secret", "/api"),
    ("../api?token=super-secret", "../api"),
    ("//user:password@example.org/api?token=super-secret", "//example.org/api"),
    ("https://" + "sensitive" * 100 + ":password@example.org/api?token=super-secret", "https://example.org/api"),
    ("search?cache", "search?cache"),
])
def test_protocol_parses_full_target_before_bounding_names(value, expected):
    from je_load_density.gui.run_protocol import safe_name

    assert safe_name(value) == expected


def test_serialized_snapshot_stays_within_reader_byte_limit_and_keeps_latest(monkeypatch):
    from je_load_density.gui.run_protocol import make_snapshot
    from je_load_density.gui.run_worker import Protocol

    records = [{"name": "測" * 490 + str(index), "start_time": index,
                "response_time_ms": index} for index in range(200)]
    snapshot = make_snapshot(records, [], users=2)
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    protocol = Protocol()
    protocol.emit("snapshot", data=snapshot)
    frame = output.getvalue().encode("utf-8")
    assert len(frame) <= 131072
    message = json.loads(frame)
    assert message["data"]["summary"]["requests"] == 200
    assert message["data"]["windows"] == snapshot["windows"]
    retained = message["data"]["records"]
    assert retained
    assert retained[-1]["name"].endswith("199")
    assert [row["start_time"] for row in retained] == list(range(200 - len(retained), 200))
    assert len(snapshot["records"]) == 200


def test_chart_uses_complete_child_windows_after_request_tail_truncation(application):
    from je_load_density.gui.run_protocol import make_snapshot

    from je_load_density.gui.chart_panel import LiveChartPanel

    records = [{"name": "first", "start_time": 100.5, "response_time_ms": 10}] * 250
    records += [{"name": "second", "start_time": 101.5, "response_time_ms": 100}] * 250
    snapshot = make_snapshot(records, [], start_time=100, end_time=102)
    assert snapshot["summary"]["requests"] == 500
    assert len(snapshot["records"]) == 200
    assert [window["count"] for window in snapshot["windows"]] == [250, 250]
    assert [window["p95_ms"] for window in snapshot["windows"]] == [10, 100]
    chart = LiveChartPanel()
    try:
        chart.reset_history(100)
        chart.set_snapshot(snapshot)
        chart.refresh()
        assert chart._rps_series.count() == 2
        assert [chart._rps_series.at(index).y() for index in range(2)] == [250, 250]
        assert [chart._latency_lines[0].at(index).y() for index in range(2)] == [10, 100]
    finally:
        chart._timer.stop()
        chart.close()


def test_action_failure_remains_visible_and_reports_continue(tmp_path):
    from je_load_density.gui.run_worker import RunSession

    class ProtocolSink:
        def emit(self, *args, **kwargs):
            pass

    action_file = tmp_path / "actions.json"
    report = tmp_path / "summary"
    actions = {"load_density": [["missing_command"], ["LD_generate_summary_report", [str(report)]]]}
    action_file.write_text(json.dumps(actions), encoding="utf-8")
    session = RunSession({"engine": "asyncio", "action_file": str(action_file)}, tmp_path / "stop", ProtocolSink())
    session.execute()
    assert session.failed_actions == 1
    assert report.with_suffix(".json").is_file()


def test_session_package_commands_are_registered_on_private_executor(tmp_path, monkeypatch):
    from je_load_density.gui.run_worker import RunSession

    from je_load_density.utils.executor.action_executor import executor
    from je_load_density.utils.package_manager.package_manager_class import package_manager

    monkeypatch.setattr(package_manager, "allowed_packages", {"json"})
    monkeypatch.setattr(package_manager, "allow_arbitrary_packages", False)
    original_commands = dict(executor.event_dict)

    class ProtocolSink:
        def emit(self, *args, **kwargs):
            pass

    action_file = tmp_path / "packages.json"
    actions = {"load_density": [["LD_add_package_to_executor", ["json"]], ["dumps", [{"ok": True}]]]}
    action_file.write_text(json.dumps(actions), encoding="utf-8")
    session = RunSession({"engine": "asyncio", "action_file": str(action_file)}, tmp_path / "stop", ProtocolSink())
    session.execute()
    assert session.failed_actions == 0
    assert executor.event_dict == original_commands
    actions["load_density"].append(["LD_add_package_to_executor", ["pickle"]])
    action_file.write_text(json.dumps(actions), encoding="utf-8")
    session.execute()
    assert session.failed_actions == 1


def test_cleanup_failure_still_notifies_failed_with_retained_summary(application, monkeypatch):
    from je_load_density.gui.load_density_gui_thread import LoadDensityGUIThread

    class FailedCleanup:
        def poll(self):
            return 0

        def wait(self, timeout):
            raise OSError("password=secret")

    worker = LoadDensityGUIThread()
    worker._process = FailedCleanup()
    worker._last_snapshot = {"summary": {"requests": 12}, "records": []}
    worker._terminal = {"state": "completed"}
    monkeypatch.setattr(worker, "_launch", lambda config: None)
    monkeypatch.setattr(worker, "_consume", lambda: None)
    outcomes, logs = [], []
    worker.completed.connect(outcomes.append)
    worker.log_message.connect(logs.append)
    worker.run()
    assert outcomes == [{"state": "failed", "summary": {"requests": 12}}]
    assert logs
    assert "secret" not in " ".join(logs)


def test_scripted_load_preserved_with_selected_engine_and_callbacks(tmp_path, monkeypatch):
    from je_load_density.gui.run_worker import RunSession

    from je_load_density.engine import entrypoints

    calls = []
    monkeypatch.setattr(entrypoints, "start_test", lambda *args, **kwargs: calls.append((args, kwargs)))
    session = RunSession({"engine": "asyncio"}, tmp_path / "stop", None)
    tasks = {"get": {"request_url": "http://localhost/example"}}
    session.start({"user": "http_user"}, 7, 3, 11, tasks=tasks, engine="locust")
    args, kwargs = calls[0]
    assert args == ({"user": "http_user"}, 7, 3, 11)
    assert kwargs["tasks"] is tasks
    assert kwargs["engine"] == "asyncio"
    assert not kwargs["stop_requested"]()
    session.control.touch()
    assert kwargs["stop_requested"]()


def test_child_incidental_output_is_visible_without_credentials(monkeypatch):
    from je_load_density.gui.run_worker import Protocol

    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    protocol = Protocol()
    protocol.write("password=secret\n")
    message = json.loads(output.getvalue())
    assert message["type"] == "log"
    assert "secret" not in message["text"]


@pytest.fixture
def worker_cli(tmp_path, monkeypatch):
    from je_load_density.gui import run_worker

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    directory = tmp_path / "loaddensity-gui-abcdefgh"
    directory.mkdir()
    config = directory / "run.json"
    config.write_text('{"engine":"asyncio"}', encoding="utf-8")
    control = directory / "stop"
    calls = []
    monkeypatch.setattr(run_worker, "run", lambda *args: calls.append(args))
    monkeypatch.setattr(sys, "argv", ["worker", "--config", str(config), "--control", str(control)])
    return run_worker, config, control, calls


@pytest.mark.parametrize("cancel_requested", [False, True])
def test_worker_cli_accepts_private_settings_and_matching_cancel_file(worker_cli, cancel_requested):
    worker, config, control, calls = worker_cli
    if cancel_requested:
        control.touch()
    worker.main()
    assert calls[0][0] == {"engine": "asyncio"}
    assert calls[0][1] == control
    assert len(calls) == 1


@pytest.mark.parametrize("invalid_path", ["outside", "filename", "control", "mismatch", "traversal", "nested"])
def test_worker_cli_rejects_untrusted_paths_before_reading(worker_cli, monkeypatch, invalid_path):
    from pathlib import Path

    worker, config, control, calls = worker_cli
    if invalid_path == "outside":
        config = config.parent.parent / "run.json"
    elif invalid_path == "filename":
        config = config.with_name("credentials.json")
    elif invalid_path == "control":
        control = control.with_name("credentials.json")
    elif invalid_path == "mismatch":
        control = control.parent.parent / "loaddensity-gui-ijklmnop" / "stop"
    elif invalid_path == "traversal":
        config = config.parent / ".." / config.parent.name / "run.json"
    else:
        config = config.parent / "nested" / "run.json"
        control = config.with_name("stop")
    monkeypatch.setattr(sys, "argv", ["worker", "--config", str(config), "--control", str(control)])

    def forbidden_read(*args, **kwargs):
        raise AssertionError("Untrusted configuration was read")

    monkeypatch.setattr(Path, "read_text", forbidden_read)
    with pytest.raises(ValueError, match="private worker"):
        worker.main()
    assert calls == []


@pytest.mark.parametrize("escaped_file", ["config", "control"])
def test_worker_cli_rejects_resolved_escape_before_reading(worker_cli, monkeypatch, escaped_file):
    from pathlib import Path

    worker, config, control, calls = worker_cli
    resolve = Path.resolve
    escaped_path = config if escaped_file == "config" else control

    def escaped_resolve(path, *args, **kwargs):
        if path == escaped_path:
            return config.parent.parent / "credentials.json"
        return resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", escaped_resolve)
    with pytest.raises(ValueError, match="private worker"):
        worker.main()
    assert calls == []


def test_unresponsive_child_is_killed_and_thread_joined(application, monkeypatch, tmp_path):
    from je_load_density.gui import load_density_gui_thread

    monkeypatch.setattr(load_density_gui_thread, "STOP_GRACE_SECONDS", 0.1)
    pid_file = tmp_path / "actual-child.pid"

    class UnresponsiveWorker(load_density_gui_thread.LoadDensityGUIThread):
        def _launch(self, config):
            script = (f"from pathlib import Path; import os,time; "
                      f"Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(60)")
            self._process = load_density_gui_thread.ChildProcess(
                [sys.executable, "-c", script])

    worker = UnresponsiveWorker()
    worker.start()
    started = time.monotonic()
    try:
        deadline = started + 2
        while not pid_file.exists() and time.monotonic() < deadline:
            load_density_gui_thread.QThread.msleep(20)
        assert pid_file.exists()
        assert worker.shutdown(timeout_ms=1500)
        assert not worker.isRunning()
        assert worker._process.poll() is not None
        assert time.monotonic() - started < 3
        if os.name == "nt":
            import ctypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel.OpenProcess(0x00100000, False, int(pid_file.read_text()))
            if handle:
                try:
                    assert kernel.WaitForSingleObject(handle, 1000) == 0
                finally:
                    kernel.CloseHandle(handle)
    finally:
        worker.shutdown(timeout_ms=1500)
