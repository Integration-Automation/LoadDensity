"""
Fuzz HTTP user template — wraps a seed task and replays mutated variants.

Each task entry has the shape of a normal HTTP task plus optional
``fuzz_count`` (default 5). The runner emits ``fuzz_count`` mutated
requests per tick.
"""

import time
from typing import Any, Dict

import urllib.request
import urllib.parse

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.utils.security.fuzz import expand_task_fuzz
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_fuzz_http_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("fuzz_http_user").configure(user_detail_dict, **kwargs)
    return FuzzHttpUserWrapper


def _send_variant(variant: Dict[str, Any], timeout: float) -> int:
    method = variant.get("method", "GET").upper()
    url = variant["request_url"]
    params = variant.get("params")
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    headers = {str(k): str(v) for k, v in (variant.get("headers") or {}).items()}
    data = None
    if "json" in variant and variant["json"] is not None:
        import json as json_module
        data = json_module.dumps(variant["json"]).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return len(response.read())


class FuzzHttpUserWrapper(User):
    """Locust user that replays mutated HTTP requests."""

    host = "https://127.0.0.1"
    wait_time = between(0.1, 0.2)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        seed = parameter_resolver.resolve(raw_task)
        count = int(seed.get("fuzz_count", 5))
        timeout = float(seed.get("timeout", 5.0))
        for variant in expand_task_fuzz(seed, count):
            name = variant.get("name") or variant.get("request_url", "")
            start = time.monotonic()
            try:
                length = _send_variant(variant, timeout)
                fire_request_event(self.environment, "FUZZ", name, start, length)
            except Exception as error:
                load_density_logger.debug(f"fuzz step failed: {error!r}")
                fire_request_event(self.environment, "FUZZ", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("fuzz_http_user")
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
