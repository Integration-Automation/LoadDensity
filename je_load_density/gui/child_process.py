"""Native Qt process I/O, independent of gevent patched Python threads and subprocesses."""

from PySide6.QtCore import QProcess


class ChildProcess:
    """Own a process in its QThread and buffer only one bounded protocol line."""

    def __init__(self, argv: list[str]) -> None:
        self._process = QProcess()
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.setProgram(argv[0])
        self._process.setArguments(argv[1:])
        self._buffer = b""
        self._process.start()
        if not self._process.waitForStarted(3000):
            raise OSError("Unable to start worker interpreter")

    def poll(self) -> int | None:
        """Read the native process state without Python scheduler involvement."""
        if self._process.state() != QProcess.NotRunning:
            return None
        return self._process.exitCode() if self._process.exitStatus() == QProcess.NormalExit else 1

    @property
    def returncode(self) -> int | None:
        """Preserve the supervisor's process inspection interface."""
        return self.poll()

    def kill(self) -> None:
        """Escalate from the owning QThread only after cooperative cancellation expires."""
        self._process.kill()

    def wait(self, timeout: float) -> None:
        """Wait with a native Qt millisecond timeout and report unexpected cleanup failure."""
        if self.poll() is None and not self._process.waitForFinished(int(timeout * 1000)):
            raise OSError("Worker cleanup timeout")

    def read_lines(self) -> list[str]:
        """Read available complete frames; native waits never need a Python reader thread."""
        if self.poll() is None:
            self._process.waitForReadyRead(50)
        data = self._buffer + bytes(self._process.readAllStandardOutput())
        lines = data.split(b"\n")
        self._buffer = lines.pop()[-131072:]
        return [line.decode("utf-8", errors="replace") for line in lines if len(line) <= 131072]
