"""
LoadDensity 的 logger 與它寫入的日誌檔。
The ``LoadDensity`` logger and the file it writes to.

The log file is ``~/.je_load_density/logs/LoadDensity.log`` unless ``LOAD_DENSITY_LOG_FILE`` names
another path (a relative one resolves against the cwd at import time; ``os.devnull`` turns the file
off). It used to be ``LoadDensity.log`` in the working directory, opened at import, so every process
that imported the package -- PyBreeze, TestPioneer, the test suite -- left a log wherever it started.

The file is opened on the first record, so importing writes nothing. Every process on the account
shares it, so it is opened for append, each line carries the process id, and it is rotated only
when a process opens it: Windows refuses to rename a file another process holds open, and a
rotation attempted inside ``emit()`` would then fail on every later record.
"""
import logging
import os
import sys
import warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

#: Environment variable that overrides where the log file is written.
LOG_FILE_ENV = "LOAD_DENSITY_LOG_FILE"

#: A file past this size is moved to ``<name>.1`` when a process opens it.
ROTATE_AT_BYTES = 10 * 1024 * 1024


def default_log_file() -> Path:
    """Return the log file path: ``$LOAD_DENSITY_LOG_FILE``, else the home-directory default."""
    configured = os.environ.get(LOG_FILE_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".je_load_density" / "logs" / "LoadDensity.log"


def _rotate_if_large(path: Path, limit: int) -> None:
    """Move ``path`` to ``<path>.1`` past ``limit`` bytes; best effort while another process holds it."""
    try:
        if limit <= 0 or not path.is_file() or path.stat().st_size <= limit:
            return
        os.replace(path, path.with_name(path.name + ".1"))
    except OSError:
        return


class LoadDensityFileHandler(RotatingFileHandler):
    """
    Append-mode UTF-8 file handler that creates its directory and rotates when it opens the file.

    A file that cannot be opened is swapped for ``os.devnull`` with one ``RuntimeWarning``: losing
    the log is acceptable, failing the import or every later record is not.
    """

    def __init__(self, filename: str, delay: bool = True) -> None:
        super().__init__(filename=filename, mode="a", encoding="utf-8",
                         errors="backslashreplace", delay=delay)

    def _open(self):
        path = Path(self.baseFilename)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            _rotate_if_large(path, ROTATE_AT_BYTES)
            return super()._open()
        except OSError as error:
            warnings.warn(f"LoadDensity log file {path} unavailable, file logging off: {error!r}",
                          RuntimeWarning, stacklevel=2)
            return open(os.devnull, self.mode, encoding=self.encoding, errors=self.errors)  # noqa: SIM115


class LoadDensityLogger:
    """
    封裝日誌系統
    Encapsulated logging system: WARNING+ to stderr, INFO+ to the log file (opened on first use).
    """

    def __init__(self,
                 logger_name: str = "LoadDensity",
                 log_file: Optional[str] = None):
        """
        初始化 Logger
        Initialize logger

        :param logger_name: Logger 名稱 (Logger name)
        :param log_file: 日誌檔案路徑，預設 ``default_log_file()`` (Log file path, default ``default_log_file()``)
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(message)s'
        )

        # Stream handler (輸出到 stderr)
        stream_handler = logging.StreamHandler(stream=sys.stderr)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.WARNING)

        file_handler = LoadDensityFileHandler(log_file if log_file is not None else str(default_log_file()))
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        # 加入 handlers
        self.logger.addHandler(stream_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """取得 logger 實例 (Get logger instance)"""
        return self.logger


load_density_logger = LoadDensityLogger().get_logger()
