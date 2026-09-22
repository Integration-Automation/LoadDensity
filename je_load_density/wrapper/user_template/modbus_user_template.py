"""
Modbus TCP user template (pymodbus, lazy import).

Each task entry::

    {"method": "connect", "host": "127.0.0.1", "port": 502}
    {"method": "read_holding", "address": 0, "count": 10, "unit": 1}
    {"method": "write_register", "address": 5, "value": 1234, "unit": 1}
    {"method": "close"}
"""

import inspect
import time
from typing import Any, Callable, Dict, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_modbus_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("modbus_user").configure(user_detail_dict, **kwargs)
    return ModbusUserWrapper


def _import_pymodbus():
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError as error:
        raise RuntimeError(
            "pymodbus is required for ModbusUser; install with: pip install pymodbus"
        ) from error
    return ModbusTcpClient



def _unit_kwarg(method: Any, step: Dict[str, Any]) -> Dict[str, int]:
    """The step's ``unit`` under the keyword this pymodbus accepts.

    pymodbus 3.15 renamed ``slave`` to ``device_id``; passing ``slave`` there raises TypeError.
    """
    unit = int(step.get("unit", 1))
    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        return {"slave": unit}
    return {"device_id": unit} if "device_id" in parameters else {"slave": unit}

class ModbusUserWrapper(User):
    """Locust user driving pymodbus TCP calls."""

    host = "127.0.0.1"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None

    def _connect(self, step: Dict[str, Any]) -> int:
        client_cls = _import_pymodbus()
        self._client = client_cls(
            host=step.get("host", self.host),
            port=int(step.get("port", 502)),
        )
        if not self._client.connect():
            raise RuntimeError("modbus connect failed")
        return 0

    def _read_holding(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("modbus not connected")
        response = self._client.read_holding_registers(
            address=int(step.get("address", 0)),
            count=int(step.get("count", 1)),
            **_unit_kwarg(self._client.read_holding_registers, step),
        )
        if response.isError():
            raise RuntimeError(str(response))
        return len(response.registers) * 2

    def _write_register(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("modbus not connected")
        response = self._client.write_register(
            address=int(step.get("address", 0)),
            value=int(step.get("value", 0)),
            **_unit_kwarg(self._client.write_register, step),
        )
        if response.isError():
            raise RuntimeError(str(response))
        return 2

    def _close(self, _: Dict[str, Any]) -> int:
        if self._client is not None:
            self._client.close()
            self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "read_holding": self._read_holding,
            "write_register": self._write_register,
            "close": self._close,
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
            fire_request_event(self.environment, "MODBUS", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"modbus step failed: {error!r}")
            fire_request_event(self.environment, "MODBUS", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("modbus_user")
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
