"""Private JSON desktop worker; engine scheduler selection precedes metrics pumping."""

import argparse
import contextlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable


class Protocol:
    """Reserve original stdout for frames and consume unsafe incidental library output."""

    def __init__(self) -> None:
        self.output = sys.stdout
        self._lock = contextlib.nullcontext()
        self._last_output_log = float("-inf")

    def select_scheduler(self) -> None:
        """Create the message lock only after Locust or native scheduler selection."""
        import threading

        self._lock = threading.Lock()

    def emit(self, kind: str, **fields) -> None:
        """Write one complete JSON frame without raw action parameters."""
        from je_load_density.gui.run_protocol import encode_frame

        frame = encode_frame(kind, **fields)
        with self._lock:
            self.output.write(frame)
            self.output.flush()

    def write(self, text: str) -> int:
        """Consume incidental prints that may contain sensitive payloads."""
        now = time.monotonic()
        if text.strip() and now - self._last_output_log >= 1:
            self._last_output_log = now
            self.emit("log", text="Test output received.")
        return len(text)

    def flush(self) -> None:
        """Support libraries expecting a file shaped stdout target."""


class RunSession:
    """Own one selected engine, cumulative records and action failure judgement."""

    def __init__(self, config: dict, control: Path, protocol: Protocol) -> None:
        self.config, self.control, self.protocol = config, control, protocol
        self.environment = None
        self.failed_actions = 0
        self.started = time.monotonic()
        self.started_epoch = math.floor(time.time())
        self.finished = False
        self.snapshot = {"summary": {}, "records": []}

    def stop_requested(self) -> bool:
        """Each run has its own cancellation file; engine callbacks never touch Qt."""
        return self.control.exists()

    def on_environment(self, environment: object) -> None:
        """Capture the engine handle for user count updates."""
        self.environment = environment

    def sample(self) -> None:
        """Emit cumulative metrics and a bounded sanitized request tail."""
        from je_load_density.gui.run_protocol import make_snapshot
        from je_load_density.utils.test_record.test_record_class import test_record_instance

        runner = getattr(self.environment, "runner", None)
        users = getattr(runner, "user_count", self.config.get("users", 0))
        if self.config["engine"] == "asyncio" and self.environment is not None:
            users = self.environment.snapshot()["users"]
        self.snapshot = make_snapshot(test_record_instance.test_record_list,
                                      test_record_instance.error_record_list,
                                      users=users, elapsed=time.monotonic() - self.started,
                                      start_time=self.started_epoch, end_time=time.time())
        self.protocol.emit("snapshot", data=self.snapshot)

    def pump(self, sleep: Callable[[float], object]) -> None:
        """Use the selected scheduler, never a gevent patched Qt thread."""
        while not self.finished:
            self.sample()
            sleep(0.25)

    def start(self, *args: Any, **kwargs: Any) -> dict:
        """Override engine and lifecycle callbacks, preserving scripted load parameters."""
        from je_load_density.engine.entrypoints import start_test

        kwargs.update(engine=self.config["engine"], stop_requested=self.stop_requested,
                      on_environment=self.on_environment)
        return start_test(*args, **kwargs)

    def execute(self) -> None:
        """Keep report actions and track swallowed failures, including nested action lists."""
        if not self.config.get("action_file"):
            self.start({"user": "fast_http_user"}, self.config["users"], self.config["spawn_rate"],
                       self.config["duration"],
                       tasks={self.config["method"]: {"request_url": self.config["url"]}})
            return
        from dataclasses import replace

        from je_action_core.reporting import ExecutionReporter

        from je_load_density.utils.executor.action_executor import Executor
        from je_load_density.utils.package_manager.package_manager_class import PackageManager, package_manager

        session = self

        class Reporter(ExecutionReporter):
            def on_failure(self, action, error):
                session.failed_actions += 1
                session.protocol.emit("log", text=f"Action failed ({type(error).__name__}).")

        executor = Executor()
        executor.settings = replace(executor.settings, reporter=Reporter())
        executor.event_dict["LD_start_test"] = self.start
        manager = PackageManager()
        manager.settings = package_manager.settings
        manager.allowed_packages = set(package_manager.allowed_packages)
        manager.allow_arbitrary_packages = package_manager.allow_arbitrary_packages
        manager.executor = executor
        executor.event_dict["LD_add_package_to_executor"] = manager.add_package_to_executor
        executor.execute_files([self.config["action_file"]])


def _scheduler(engine: str):
    if engine == "locust":
        import gevent
        import locust  # noqa: F401 - select scheduler before starting the metrics pump.

        return gevent.spawn, gevent.sleep
    if engine != "asyncio":
        raise ValueError("Unsupported engine")
    import threading

    def spawn(function, *args):
        thread = threading.Thread(target=function, args=args, daemon=True)
        thread.start()
        return thread

    return spawn, time.sleep


def run(config: dict, control: Path, protocol: Protocol) -> None:
    """Select scheduler first and publish a terminal snapshot for every engine failure."""
    spawn, sleep = _scheduler(config["engine"])
    protocol.select_scheduler()
    session = RunSession(config, control, protocol)
    protocol.emit("state", state="running")
    pump = spawn(session.pump, sleep)
    state = "completed"
    try:
        session.execute()
        if session.failed_actions:
            state = "failed"
        elif session.stop_requested():
            state = "cancelled"
    except Exception as error:  # Engine boundary: every failure becomes a visible terminal state.
        state = "failed"
        protocol.emit("log", text=f"Test failed ({type(error).__name__}). Check the action file and target.")
    finally:
        session.finished = True
        pump.join(timeout=1)
        session.sample()
        protocol.emit("terminal", data={"state": state, "summary": session.snapshot["summary"]})


def main() -> None:
    """Read private settings and reserve stdout for bounded worker frames."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--control", required=True)
    args = parser.parse_args()
    protocol = Protocol()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    with contextlib.redirect_stdout(protocol), contextlib.redirect_stderr(protocol):
        run(config, Path(args.control), protocol)


if __name__ == "__main__":
    main()
