"""Native asyncio HTTP runs with owned clients, tasks, records and cancellation."""

import asyncio
import ssl
import time
from contextlib import AsyncExitStack, nullcontext
from typing import Any, Dict, List, Optional

from je_load_density.engine.async_config import number, shape_target, validate_shape, validate_tasks
from je_load_density.engine.async_http import AsyncThrottle, UserClientPool, execute_step
from je_load_density.utils.generate_report.generate_summary_report import build_summary
from je_load_density.utils.parameterization import (
    get_resolver,
    register_csv_sources,
    register_db_sources,
    register_variables,
    use_resolver,
)
from je_load_density.wrapper.user_template.scenario_runner import _condition_passes, _pick_weighted

_OPTIONS = frozenset(
    {
        "spawn_rate",
        "load_shape",
        "shape_config",
        "runner_mode",
        "base_url",
        "stop_requested",
        "on_environment",
        "variables",
        "csv_sources",
        "db_sources",
    }
)


def _import_httpx():
    try:
        import httpx
    except ImportError as error:
        raise RuntimeError("httpx is required for the asyncio engine") from error
    return httpx


class AsyncRunHandle:
    """One run's awaitable lifecycle; stop cooperatively cancels owned I/O."""

    def __init__(self, tasks, users=10, duration_seconds=10.0, **options) -> None:
        self.payload = validate_tasks(tasks)
        self.users = int(number(users, "users", integer=True, minimum=1))
        self.duration = number(duration_seconds, "duration_seconds", minimum=0.000001)
        self.http2 = options.pop("http2", False)
        if not isinstance(self.http2, bool):
            raise ValueError("http2 must be boolean")
        self.run_context = options.pop("run_context", None)
        limit = options.pop("max_in_flight", None)
        self._configure(options)
        self.limit = (
            self._peak_users() if limit is None else int(number(limit, "max_in_flight", integer=True, minimum=1))
        )
        self.successes, self.failures = [], []
        self.workers = []
        self.state = "created"
        self.started = None
        self.finished = None
        self._task = None
        self._loop = None
        self._stop = asyncio.Event()
        self._throttles = {}
        self.resolver = get_resolver().fork()
        self._warm_pool = None

    def _configure(self, options: dict) -> None:
        unknown = set(options) - _OPTIONS
        if unknown:
            raise ValueError(f"Unsupported native run options: {sorted(unknown)}")
        if options.get("runner_mode", "local") != "local":
            raise ValueError("Native asyncio currently supports local HTTP runs only")
        self.options = options
        self.spawn_rate = number(options.get("spawn_rate", self.users), "spawn_rate", minimum=0.000001)
        self.shape = options.get("load_shape")
        self.shape_config = options.get("shape_config") or {}
        validate_shape(self.shape, self.shape_config)
        self.base_url = options.get("base_url", "")
        if not isinstance(self.base_url, str):
            raise ValueError("base_url must be a string")
        if not self.base_url and any(
            (task.get("request_url") or task.get("url")).startswith("/") for task in self.payload["tasks"]
        ):
            raise ValueError("Relative HTTP tasks require base_url")
        for name in ("stop_requested", "on_environment"):
            if options.get(name) is not None and not callable(options[name]):
                raise ValueError(f"{name} must be callable")

    def _peak_users(self) -> int:
        if self.shape == "stages":
            return max(self.users, *(int(stage.get("users", 0)) for stage in self.shape_config["stages"]))
        return max(
            self.users,
            int(self.shape_config.get("users", 0)),
            int(self.shape_config.get("baseline_users", 0)),
            int(self.shape_config.get("spike_users", 0)),
        )

    async def start(self):
        if self._task is not None:
            raise RuntimeError("A run handle can only be started once")
        self._loop = asyncio.get_running_loop()
        self.semaphore = asyncio.Semaphore(self.limit)
        self._task = asyncio.create_task(self._execute())
        return self

    def stop(self) -> None:
        if self._loop is None:
            self._stop.set()
        else:
            self._loop.call_soon_threadsafe(self._stop.set)

    async def wait(self) -> dict:
        if self._task is None:
            raise RuntimeError("Start the run before waiting")
        return await self._task

    def snapshot(self) -> dict:
        elapsed = 0 if self.started is None else (self.finished or time.monotonic()) - self.started
        total = len(self.successes) + len(self.failures)
        return {
            "engine": "asyncio",
            "state": self.state,
            "users": sum(not task.done() for task in self.workers),
            "target": self.base_url,
            "elapsed_seconds": elapsed,
            "rps": total / max(elapsed, 0.000001),
            "requests": len(self.successes),
            "failures": len(self.failures),
            "summary": build_summary(self.successes, self.failures),
        }

    def throttle(self, config: dict) -> AsyncThrottle:
        key = str(config.get("key", "default"))
        settings = (float(config["rps"]), int(config.get("burst", 1)))
        if key not in self._throttles:
            self._throttles[key] = (settings, AsyncThrottle(*settings))
        previous, throttle = self._throttles[key]
        if settings != previous:
            raise ValueError(f"Throttle {key!r} has conflicting settings")
        return throttle

    def _prepare_sources(self) -> None:
        register_variables(self.options.get("variables") or {})
        register_csv_sources(self.options.get("csv_sources") or [])
        register_db_sources(self.options.get("db_sources") or [])

    async def _prepare_clients(self) -> None:
        """Reject static TLS/proxy setup failures before starting target traffic."""
        await self._warm_pool.client({})
        for task in self.payload["tasks"]:
            # Validate independent static options even alongside user-dependent values.
            transport = {key: task[key] for key in ("verify", "cert", "client_cert", "proxy")
                         if key in task and "${" not in repr(task[key])}
            await self._warm_pool.client(transport)

    async def _execute(self) -> dict:
        primary_failure = False
        resources = AsyncExitStack()
        scope = nullcontext()
        if self.run_context is not None:
            from je_load_density.utils.test_record.run_context import use_run_context

            scope = use_run_context(self.run_context)
        try:
            with scope, use_resolver(self.resolver):
                self._prepare_sources()
                httpx = _import_httpx()
                # Transport initialization precedes the load clock; users share TLS trust,
                # but keep separate clients, sockets and cookies.
                self.verify_context = ssl.create_default_context()
                self._warm_pool = await resources.enter_async_context(
                    UserClientPool(httpx, self.http2, self.verify_context)
                )
                await self._prepare_clients()
                self.started = time.monotonic()
                self.state = "running"
                callback = self.options.get("on_environment")
                if callback is not None:
                    callback(self)
                await self._schedule(httpx)
                self.state = "cancelled" if self._stop.is_set() else "completed"
        except asyncio.CancelledError:
            primary_failure = True
            self.state = "cancelled"
            raise
        except Exception:
            primary_failure = True
            self.state = "failed"
            raise
        finally:
            results = await self._cancel_workers()
            try:
                if not primary_failure:
                    self._raise_worker_errors(results)
            finally:
                await resources.aclose()
                self.finished = time.monotonic()
        return self.snapshot()

    async def _cancel_workers(self) -> list:
        for task in self.workers:
            if not task.done():
                task.cancel()
        return await asyncio.gather(*self.workers, return_exceptions=True)

    def _raise_worker_errors(self, results: list) -> None:
        for result in results:
            if isinstance(result, Exception):
                self.state = "failed"
                raise result

    def _check_workers(self) -> None:
        for task in self.workers:
            if task.done() and not task.cancelled():
                task.result()
        self.workers = [task for task in self.workers if not task.done()]

    async def _schedule(self, httpx) -> None:
        credits, previous = 1.0, self.started
        while not self._stop.is_set():
            self._check_workers()
            now = time.monotonic()
            elapsed = now - self.started
            if elapsed >= self.duration:
                return
            callback = self.options.get("stop_requested")
            if callback is not None and callback():
                self._stop.set()
                return
            target = shape_target(self.shape, self.shape_config, elapsed, self.users, self.spawn_rate)
            if target is None:
                return
            count, rate = target
            credits = min(max(count, 1), credits + (now - previous) * rate)
            previous = now
            await self._resize(httpx, count, int(credits))
            credits -= self._spawned
            await asyncio.sleep(min(0.02, max(0, self.duration - elapsed)))

    async def _resize(self, httpx, count: int, available: int) -> None:
        excess = self.workers[count:]
        for task in excess:
            task.cancel()
        if excess:
            results = await asyncio.gather(*excess, return_exceptions=True)
            self._raise_worker_errors(results)
            self.workers = self.workers[:count]
        self._spawned = min(max(count - len(self.workers), 0), available)
        for _ in range(self._spawned):
            self.workers.append(asyncio.create_task(self._user(httpx, self.resolver.fork())))

    async def _user(self, httpx, resolver) -> None:
        pool = self._warm_pool
        self._warm_pool = None
        if pool is None:
            pool = UserClientPool(httpx, self.http2, self.verify_context)
        with use_resolver(resolver):
            async with pool:
                while not self._stop.is_set():
                    tasks = self.payload["tasks"]
                    if self.payload["mode"] == "weighted":
                        chosen = _pick_weighted(tasks)
                        tasks = [] if chosen is None else [chosen]
                    for task in tasks:
                        if _condition_passes(task):
                            await execute_step(pool, task, self)
                    await asyncio.sleep(0.001)


async def run_async_load(
    tasks: List[Dict[str, Any]],
    users: int = 10,
    duration_seconds: float = 10.0,
    http2: bool = False,
    max_in_flight: Optional[int] = None,
    run_context=None,
    **options,
) -> Dict[str, Any]:
    """Await HTTP load; legacy requests counts successes, summary counts attempts."""
    handle = AsyncRunHandle(
        tasks, users, duration_seconds, http2=http2, max_in_flight=max_in_flight, run_context=run_context, **options
    )
    await handle.start()
    return await handle.wait()
