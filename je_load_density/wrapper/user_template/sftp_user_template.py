"""
SFTP user template (paramiko, lazy import).

Each task entry::

    {"method": "connect", "host": "127.0.0.1", "port": 22,
     "username": "u", "password": "p"}
    {"method": "list", "path": "."}
    {"method": "upload", "local": "./x", "remote": "/tmp/x"}
    {"method": "download", "remote": "/tmp/x", "local": "./y"}
    {"method": "disconnect"}

A ``connection`` dict given to the setter supplies default step fields; keys in the step win.
"""

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
from je_load_density.wrapper.user_template._common import (
    fire_request_event,
    with_connection_defaults,
)


def set_wrapper_sftp_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("sftp_user").configure(user_detail_dict, **kwargs)
    return SftpUserWrapper


def _import_paramiko():
    try:
        import paramiko
    except ImportError as error:
        raise RuntimeError(
            "paramiko is required for SftpUser; install with: pip install paramiko"
        ) from error
    return paramiko


class SftpUserWrapper(User):
    """Locust user driving paramiko SFTPClient calls."""

    host = "127.0.0.1"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._transport = None
        self._sftp = None

    def _connect(self, step: Dict[str, Any]) -> int:
        paramiko = _import_paramiko()
        host = step.get("host", "127.0.0.1")
        port = int(step.get("port", 22))
        self._transport = paramiko.Transport((host, port))
        self._transport.connect(
            username=step.get("username", ""),
            password=step.get("password"),
            pkey=step.get("pkey"),
        )
        self._sftp = paramiko.SFTPClient.from_transport(self._transport)
        return 0

    def _list(self, step: Dict[str, Any]) -> int:
        if self._sftp is None:
            raise RuntimeError("sftp client not connected")
        entries: List[str] = self._sftp.listdir(step.get("path", "."))
        return sum(len(name) for name in entries)

    def _upload(self, step: Dict[str, Any]) -> int:
        if self._sftp is None:
            raise RuntimeError("sftp client not connected")
        local_path = step["local"]
        remote = step.get("remote") or os.path.basename(local_path)
        self._sftp.put(local_path, remote)
        return os.path.getsize(local_path)

    def _download(self, step: Dict[str, Any]) -> int:
        if self._sftp is None:
            raise RuntimeError("sftp client not connected")
        local_path = step["local"]
        self._sftp.get(step["remote"], local_path)
        return os.path.getsize(local_path)

    def _disconnect(self, _: Dict[str, Any]) -> int:
        if self._sftp is not None:
            self._sftp.close()
            self._sftp = None
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "list": self._list,
            "upload": self._upload,
            "download": self._download,
            "disconnect": self._disconnect,
        }.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = with_connection_defaults("sftp_user", parameter_resolver.resolve(raw_task))
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "SFTP", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"sftp step failed: {error!r}")
            fire_request_event(self.environment, "SFTP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("sftp_user")
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
