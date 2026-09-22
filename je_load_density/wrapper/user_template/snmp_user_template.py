"""
SNMP user template (pysnmp, lazy import).

Each task entry::

    {"method": "get",  "host": "127.0.0.1", "community": "public",
     "oid": "1.3.6.1.2.1.1.1.0"}
    {"method": "walk", "host": "127.0.0.1", "community": "public",
     "oid": "1.3.6.1.2.1.1"}
"""

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


def set_wrapper_snmp_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("snmp_user").configure(user_detail_dict, **kwargs)
    return SnmpUserWrapper


def _import_pysnmp():
    try:
        from pysnmp.hlapi import (
            CommunityData,
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            getCmd,
            nextCmd,
        )
    except ImportError as error:
        raise RuntimeError(
            "pysnmp is required for SnmpUser; install with: pip install pysnmp"
        ) from error
    return {
        "SnmpEngine": SnmpEngine,
        "CommunityData": CommunityData,
        "UdpTransportTarget": UdpTransportTarget,
        "ContextData": ContextData,
        "ObjectType": ObjectType,
        "ObjectIdentity": ObjectIdentity,
        "getCmd": getCmd,
        "nextCmd": nextCmd,
    }


def _coerce_varbinds(varbinds: List[Any]) -> int:
    return sum(len(str(vb)) for vb in varbinds)


class SnmpUserWrapper(User):
    """Locust user driving pysnmp calls."""

    host = "127.0.0.1"
    wait_time = between(0.1, 0.2)

    def _build_args(self, lib: Dict[str, Any], step: Dict[str, Any]):
        return (
            lib["SnmpEngine"](),
            lib["CommunityData"](step.get("community", "public"), mpModel=0),
            lib["UdpTransportTarget"]((step["host"], int(step.get("port", 161)))),
            lib["ContextData"](),
            lib["ObjectType"](lib["ObjectIdentity"](step["oid"])),
        )

    def _get(self, step: Dict[str, Any]) -> int:
        lib = _import_pysnmp()
        engine, community, transport, context, oid = self._build_args(lib, step)
        iterator = lib["getCmd"](engine, community, transport, context, oid)
        error_indication, error_status, _error_index, varbinds = next(iterator)
        if error_indication:
            raise RuntimeError(str(error_indication))
        if error_status:
            raise RuntimeError(str(error_status.prettyPrint()))
        return _coerce_varbinds(list(varbinds))

    def _walk(self, step: Dict[str, Any]) -> int:
        lib = _import_pysnmp()
        engine, community, transport, context, oid = self._build_args(lib, step)
        total = 0
        for error_indication, error_status, _error_index, varbinds in lib["nextCmd"](
            engine, community, transport, context, oid, lexicographicMode=False,
        ):
            if error_indication or error_status:
                break
            total += _coerce_varbinds(list(varbinds))
        return total

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {"get": self._get, "walk": self._walk}.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "")).lower()
        name = step.get("name") or step.get("oid", method)
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "SNMP", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"snmp step failed: {error!r}")
            fire_request_event(self.environment, "SNMP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("snmp_user")
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
