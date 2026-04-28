import importlib
import re
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


def set_wrapper_grpc_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    """
    設定 gRPC User 的代理使用者
    Configure gRPC User proxy
    """
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])

    locust_wrapper_proxy.user_dict.get("grpc_user").configure(user_detail_dict, **kwargs)
    return GrpcUserWrapper


_SAFE_DOTTED_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def _import_dotted(path: str) -> Any:
    """
    Resolve a dotted ``module.attr`` path supplied in a load-test scenario.

    The gRPC user genuinely needs to load operator-authored stub
    modules at runtime, so a static import literal is not viable. We
    accept this by validating that ``path`` is a syntactically safe
    Python identifier chain (no separators, no relative dots, no
    dunders bridged via traversal) before delegating to importlib.
    """
    if not isinstance(path, str) or not _SAFE_DOTTED_PATH.match(path):
        raise ImportError(f"invalid dotted import path: {path!r}")
    module_name, _, attr = path.rpartition(".")
    if not module_name:
        raise ImportError(f"invalid dotted import path: {path!r}")
    # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
    module = importlib.import_module(module_name)
    return getattr(module, attr)


class GrpcUserWrapper(User):
    """
    Locust gRPC User 包裝類別
    Locust gRPC User wrapper class

    Each task entry should look like::

        {
            "name": "say_hello",
            "stub_path": "pkg.greeter_pb2_grpc.GreeterStub",
            "request_path": "pkg.greeter_pb2.HelloRequest",
            "method": "SayHello",
            "payload": {"name": "world"},
            "metadata": [["x-token", "..."]],
            "timeout": 10
        }
    """

    host = "localhost:50051"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._channel = None
        self._target = ""

    def _ensure_grpc(self):
        try:
            import grpc
        except ImportError as error:
            raise RuntimeError("grpcio is required for GrpcUser") from error
        return grpc

    def _ensure_channel(self, target: str):
        grpc = self._ensure_grpc()
        if self._channel is None or self._target != target:
            if self._channel is not None:
                try:
                    self._channel.close()
                except Exception as error:
                    load_density_logger.debug(f"grpc channel close before reconnect failed: {error!r}")
            self._channel = grpc.insecure_channel(target)
            self._target = target
        return self._channel

    def _fire(self, name: str, target: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="GRPC",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=target,
            response=None,
            start_time=start,
        )

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        target = step.get("target") or step.get("host") or self.host
        method_name = step.get("method", "")
        stub_path = step.get("stub_path", "")
        request_path = step.get("request_path", "")
        payload = step.get("payload") or {}
        metadata = _coerce_metadata(step.get("metadata"))
        timeout = float(step.get("timeout", 10))
        name = step.get("name") or f"{stub_path}.{method_name}"

        start = time.monotonic()
        try:
            channel = self._ensure_channel(target)
            stub_cls = _import_dotted(stub_path)
            request_cls = _import_dotted(request_path)
            stub = stub_cls(channel)
            method = getattr(stub, method_name)

            request = request_cls(**payload) if isinstance(payload, dict) else request_cls()
            response = method(request, timeout=timeout, metadata=metadata)
            length = response.ByteSize() if hasattr(response, "ByteSize") else 0
            self._fire(name, target, start, length)
        except Exception as error:
            self._fire(name, target, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("grpc_user")
        if not proxy_user or not proxy_user.tasks:
            return
        tasks = proxy_user.tasks
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks.get("tasks") or []
        if not isinstance(tasks, list):
            load_density_logger.warning("grpc_user.tasks must be a list")
            return
        for raw_task in tasks:
            if isinstance(raw_task, dict):
                self._do_step(raw_task)


def _coerce_metadata(metadata: Any) -> Tuple[Tuple[str, str], ...]:
    if not metadata:
        return ()
    if isinstance(metadata, dict):
        return tuple((str(k), str(v)) for k, v in metadata.items())
    if isinstance(metadata, list):
        result = []
        for item in metadata:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                result.append((str(item[0]), str(item[1])))
        return tuple(result)
    return ()
