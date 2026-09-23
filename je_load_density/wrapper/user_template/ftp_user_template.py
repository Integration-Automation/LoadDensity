"""
FTP user template (stdlib ftplib).

Each task entry::

    {"method": "connect", "host": "ftp.example.com", "port": 21}
    {"method": "login", "username": "u", "password": "p"}
    {"method": "list", "path": "/"}
    {"method": "upload", "local": "./file.txt", "remote": "file.txt"}
    {"method": "download", "remote": "file.txt", "local": "./out.txt"}
    {"method": "quit"}
"""

import ftplib
import io
import os.path
import time
from typing import Any, Callable, Dict, List, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_ftp_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("ftp_user").configure(user_detail_dict, **kwargs)
    return FtpUserWrapper


class FtpUserWrapper(User):
    """Locust user driving ftplib calls."""

    host = "ftp.example.com"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client: Optional[ftplib.FTP] = None

    def _connect(self, step: Dict[str, Any]) -> int:
        host = step.get("host", "127.0.0.1")
        port = int(step.get("port", 21))
        timeout = float(step.get("timeout", 10))
        # Plain FTP is what this user load-tests; FTPS servers need a TLS template of their own.
        self._client = ftplib.FTP(timeout=timeout)  # NOSONAR S5332 — the protocol under test
        self._client.connect(host, port)
        return 0

    def _login(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("ftp client not connected")
        self._client.login(step.get("username", ""), step.get("password", ""))
        return 0

    def _list(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("ftp client not connected")
        entries: List[str] = []
        self._client.retrlines(f"LIST {step.get('path', '.')}", entries.append)
        return sum(len(line) for line in entries)

    def _upload(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("ftp client not connected")
        local_path = step["local"]
        remote = step.get("remote") or os.path.basename(local_path)
        with open(local_path, "rb") as handle:
            self._client.storbinary(f"STOR {remote}", handle)
        return os.path.getsize(local_path)

    def _download(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("ftp client not connected")
        buffer = io.BytesIO()
        self._client.retrbinary(f"RETR {step['remote']}", buffer.write)
        payload = buffer.getvalue()
        local_path = step.get("local")
        if local_path:
            with open(local_path, "wb") as handle:
                handle.write(payload)
        return len(payload)

    def _quit(self, _: Dict[str, Any]) -> int:
        if self._client is None:
            return 0
        try:
            self._client.quit()
        finally:
            self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "login": self._login,
            "list": self._list,
            "upload": self._upload,
            "download": self._download,
            "quit": self._quit,
        }.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "FTP", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"ftp step failed: {error!r}")
            fire_request_event(self.environment, "FTP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("ftp_user")
        if not proxy_user or not proxy_user.tasks:
            return
        tasks = proxy_user.tasks
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks.get("tasks") or []
        if not isinstance(tasks, list):
            return
        for raw_task in tasks:
            if isinstance(raw_task, dict):
                self._do_step(raw_task)
