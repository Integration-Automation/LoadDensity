"""
CoAP user template (aiocoap, lazy import).

Each task entry::

    {"method": "get",    "uri": "coap://127.0.0.1/.well-known/core"}
    {"method": "post",   "uri": "coap://127.0.0.1/sensor",  "payload": "1"}
    {"method": "put",    "uri": "coap://127.0.0.1/sensor",  "payload": "2"}
    {"method": "delete", "uri": "coap://127.0.0.1/sensor"}
"""

import asyncio
import time
from typing import Any, Dict, Tuple

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_coap_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("coap_user").configure(user_detail_dict, **kwargs)
    return CoapUserWrapper


def _import_aiocoap():
    try:
        import aiocoap
    except ImportError as error:
        raise RuntimeError(
            "aiocoap is required for CoapUser; install with: pip install aiocoap"
        ) from error
    return aiocoap


_METHOD_CODES = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "delete": "DELETE",
}


async def _send_coap(step: Dict[str, Any]) -> Tuple[str, int]:
    aiocoap = _import_aiocoap()
    method_name = _METHOD_CODES.get(str(step.get("method", "")).lower())
    if method_name is None:
        raise ValueError(f"unsupported coap method: {step.get('method')}")
    payload = step.get("payload", "")
    payload_bytes = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
    context = await aiocoap.Context.create_client_context()
    try:
        request = aiocoap.Message(
            code=getattr(aiocoap.numbers.codes.Code, method_name),
            uri=step["uri"],
            payload=payload_bytes,
        )
        response = await context.request(request).response
        return str(response.code), len(response.payload)
    finally:
        await context.shutdown()


class CoapUserWrapper(User):
    """Locust user driving aiocoap calls."""

    host = "coap://127.0.0.1"
    wait_time = between(0.1, 0.2)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        name = step.get("name") or step.get("uri", "")
        start = time.monotonic()
        try:
            _code, length = asyncio.run(_send_coap(step))
            fire_request_event(self.environment, "COAP", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"coap step failed: {error!r}")
            fire_request_event(self.environment, "COAP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("coap_user")
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
