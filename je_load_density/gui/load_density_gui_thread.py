"""Qt worker that supervises an isolated engine process without importing Locust."""

import json
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from je_load_density.gui.child_process import ChildProcess

DEFAULT_USER_TYPE = "fast_http_user"
STOP_GRACE_SECONDS = 3.0


class LoadDensityGUIThread(QThread):
    """Deliver bounded child messages through Qt signals; stop and join on shutdown."""

    state_changed = Signal(str)
    snapshot_ready = Signal(dict)
    log_message = Signal(str)
    completed = Signal(dict)

    def __init__(self, request_url: str | None = None, test_duration: int | None = None,
                 user_count: int | None = None, spawn_rate: int | None = None,
                 http_method: str | None = None, **kwargs: object) -> None:
        super().__init__()
        self.request_url, self.test_duration = request_url, test_duration
        self.user_count, self.spawn_rate = user_count, spawn_rate
        self.http_method = http_method
        self.engine = kwargs.get("engine", "locust")
        self.action_file = kwargs.get("action_file", "")
        self._stop = False
        self._process = None
        self._control = None
        self._last_snapshot = {"summary": {}, "records": []}
        self._terminal = None

    def request_stop(self) -> None:
        """Ask the child to stop cooperatively through a run specific control file."""
        self._stop = True
        if self._control is not None:
            try:
                self._control.touch(exist_ok=True)
            except FileNotFoundError:
                return  # The already finished run removed its private control directory.

    def shutdown(self, timeout_ms: int = 6000) -> bool:
        """Cancel, escalate after the grace period and join the QThread within a bound."""
        self.request_stop()
        if self.wait(timeout_ms):
            return True
        self.requestInterruption()
        return self.wait(2000)

    def _terminate(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.kill()

    def _config(self) -> dict:
        return {"url": self.request_url, "duration": self.test_duration, "users": self.user_count,
                "spawn_rate": self.spawn_rate, "method": self.http_method,
                "engine": self.engine, "action_file": self.action_file}

    def run(self) -> None:
        """Run a fresh interpreter and report every exit as a terminal lifecycle event."""
        try:
            with tempfile.TemporaryDirectory(prefix="loaddensity-gui-") as directory:
                config = Path(directory) / "run.json"
                config.write_text(json.dumps(self._config()), encoding="utf-8")
                config.chmod(0o600)
                self._control = Path(directory) / "stop"
                if self._stop:
                    self.request_stop()
                self._launch(config)
                self._consume()
        except (OSError, ValueError):
            self.log_message.emit("Unable to run the selected test. Check the configuration and dependencies.")
        finally:
            self._cleanup()
            self._control = None
            result = self._terminal or {"state": "cancelled" if self._stop else "failed"}
            result.setdefault("summary", self._last_snapshot["summary"])
            self.completed.emit(result)

    def _cleanup(self) -> None:
        try:
            self._terminate()
            if self._process is not None:
                self._process.wait(timeout=2)
        except OSError:
            self._terminal = {"state": "failed"}
            self.log_message.emit("Unable to finish worker cleanup. The run has failed.")

    def _launch(self, config: Path) -> None:
        argv = [sys.executable, "-m", "je_load_density.gui.run_worker", "--config", str(config),
                "--control", str(self._control)]
        self._process = ChildProcess(argv)

    def _consume(self) -> None:
        deadline = None
        while self._process.poll() is None:
            if self._stop and deadline is None:
                deadline = time.monotonic() + STOP_GRACE_SECONDS
            if self.isInterruptionRequested() or (deadline is not None and time.monotonic() >= deadline):
                self._terminate()
            for line in self._process.read_lines():
                self._message(line)
        for line in self._process.read_lines():
            self._message(line)
        if self._process.returncode != 0:
            self._terminal = None

    def _message(self, line: str) -> None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return  # Third party diagnostics may contain request credentials.
        if not isinstance(message, dict):
            return
        kind = message.get("type")
        if kind == "snapshot":
            self._last_snapshot = message["data"]
            self.snapshot_ready.emit(message["data"])
        elif kind == "state":
            self.state_changed.emit(message["state"])
        elif kind == "log":
            self.log_message.emit(message["text"][:1200])
        elif kind == "terminal":
            self._terminal = message["data"]
