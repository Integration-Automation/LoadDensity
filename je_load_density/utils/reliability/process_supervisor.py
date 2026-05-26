"""
Process supervisor.

* :class:`ProcessSupervisor` walks the OS process table for stuck
  Locust / gevent workers and kills stragglers (never the current
  process).
* :func:`with_watchdog` wraps a long callable with a hard wall-clock
  raise so a hung user template doesn't pin a CI job forever.
"""

import os
import signal
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


_TARGET_NAMES = ("locust", "gevent")


@dataclass
class ProcessSupervisor:
    name_substrings: tuple = _TARGET_NAMES
    grace_seconds: float = 2.0
    killed: List[int] = field(default_factory=list)

    def _iter_processes(self):
        try:
            import psutil  # type: ignore
        except ImportError as error:
            raise RuntimeError(
                "psutil is required for ProcessSupervisor; install with: pip install psutil"
            ) from error
        own_pid = os.getpid()
        for process in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            if process.info.get("pid") == own_pid:
                continue
            yield process

    def _matches(self, info: dict) -> bool:
        name = (info.get("name") or "").lower()
        cmd = " ".join(info.get("cmdline") or []).lower()
        return any(token in name or token in cmd for token in self.name_substrings)

    def kill_orphans(self) -> List[int]:
        killed: List[int] = []
        for process in self._iter_processes():
            if not self._matches(process.info or {}):
                continue
            try:
                process.terminate()
                killed.append(process.info["pid"])
            except Exception:
                continue
        if killed:
            try:
                import psutil  # type: ignore
                _, alive = psutil.wait_procs([
                    p for p in self._iter_processes() if (p.info or {}).get("pid") in killed
                ], timeout=self.grace_seconds)
                for survivor in alive:
                    try:
                        survivor.kill()
                    except Exception:
                        continue
            except Exception:
                pass
        self.killed.extend(killed)
        return killed


def with_watchdog(
    callable_: Callable[..., Any],
    *args: Any,
    timeout_seconds: float = 300.0,
    on_timeout: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """
    Run ``callable_`` and raise :class:`TimeoutError` if it exceeds
    ``timeout_seconds``. The callable continues running in its
    daemon thread until the process exits.
    """
    result: List[Any] = []
    error_box: List[BaseException] = []

    def _target() -> None:
        try:
            result.append(callable_(*args, **kwargs))
        except BaseException as error:
            error_box.append(error)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        if on_timeout is not None:
            try:
                on_timeout()
            except Exception:
                pass
        raise TimeoutError(
            f"{getattr(callable_, '__name__', 'callable')} exceeded {timeout_seconds}s"
        )

    if error_box:
        raise error_box[0]
    return result[0] if result else None


def kill_pid(pid: int, sig: int = signal.SIGTERM) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        os.kill(pid, sig)
        return True
    except (OSError, ProcessLookupError):
        return False
