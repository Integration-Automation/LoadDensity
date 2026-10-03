"""User-owned native HTTP clients, measured attempts and asynchronous pacing."""

import asyncio
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass
from urllib.parse import urljoin

from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.utils.reliability.adaptive_retry import AdaptiveRetryPolicy, classify_error
from je_load_density.utils.test_record.contract import record_request
from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.wrapper.user_template.request_executor import (
    _apply_extractors,
    _build_kwargs,
    _check_assertions,
)
from je_load_density.wrapper.user_template.scenario_runner import _think_time_seconds


@dataclass
class Attempt:
    entry: dict
    error: Exception | None


class AsyncThrottle:
    """Run-local token bucket; waiting never blocks the asyncio scheduler."""

    def __init__(self, rps: float, burst: int) -> None:
        self.rps = rps
        self.burst = burst
        self.tokens = float(burst)
        self.updated = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self.lock:
                now = time.monotonic()
                self.tokens = min(self.burst, self.tokens + (now - self.updated) * self.rps)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                delay = (1 - self.tokens) / self.rps
            await asyncio.sleep(delay)


class UserClientPool:
    """Reusable transport configurations belong to one virtual user's cookie jar."""

    def __init__(self, httpx, http2: bool, verify_context=None) -> None:
        self.httpx = httpx
        self.http2 = http2
        self.verify_context = verify_context
        self.clients = {}
        self.cookies = httpx.Cookies()
        self.stack = AsyncExitStack()

    async def __aenter__(self):
        await self.stack.__aenter__()
        return self

    async def __aexit__(self, *args):
        return await self.stack.__aexit__(*args)

    async def client(self, task: dict):
        options = {"verify": task.get("verify", True), "http2": self.http2}
        cert = task.get("cert", task.get("client_cert"))
        if options["verify"] is True and self.verify_context is not None and cert is None:
            options["verify"] = self.verify_context
        if cert is not None:
            options["cert"] = cert
        if task.get("proxy") is not None:
            options["proxy"] = task["proxy"]
        key = tuple((name, repr(value)) for name, value in options.items())
        if key not in self.clients:
            self.clients[key] = await self.stack.enter_async_context(self.httpx.AsyncClient(**options))
        client = self.clients[key]
        client.cookies.update(self.cookies)
        return client

    async def send(self, task: dict, base_url: str):
        client = await self.client(task)
        kwargs = _build_kwargs(task)
        for key in ("name", "verify", "cert"):
            kwargs.pop(key, None)
        kwargs["follow_redirects"] = kwargs.pop("allow_redirects", True)
        kwargs.setdefault("timeout", 10.0)
        url = task.get("request_url") or task.get("url")
        url = urljoin(base_url, url)
        response = await client.request(str(task.get("method", "get")).upper(), url, **kwargs)
        # Share the actual CookieJar, including expiry/deletion, between this user's clients.
        self.cookies = client.cookies
        for other in self.clients.values():
            other.cookies.jar = self.cookies.jar
        return response


def _response_result(response, task: dict) -> tuple[Exception | None, list]:
    results = []
    error = None
    for assertion in task.get("assertions") or []:
        passed, reason = _check_assertions(response, [assertion])
        results.append({"type": assertion["type"], "passed": passed})
        if not passed and error is None:
            error = AssertionError(reason)
    expected_status = any(rule["type"] == "status_code" for rule in task.get("assertions") or [])
    if error is None and response.status_code >= 400 and not expected_status:
        error = RuntimeError(f"HTTP {response.status_code}")
    if error is None:
        _apply_extractors(response, task.get("extract") or [])
    return error, results


async def measure(pool: UserClientPool, task: dict, base_url: str) -> Attempt:
    started, clock = time.time(), time.monotonic()
    url = urljoin(base_url, task.get("request_url") or task.get("url"))
    entry = {
        "Method": str(task.get("method", "get")).upper(),
        "test_url": url,
        "name": task.get("name") or url,
        "start_time": started,
        "status_code": "0",
        "response_length": 0,
    }
    try:
        response = await pool.send(task, base_url)
    except pool.httpx.HTTPError as error:
        entry["error_kind"] = "timeout" if isinstance(error, pool.httpx.TimeoutException) else "connection"
        outcome_error = error
    else:
        entry.update(status_code=str(response.status_code), response_length=len(response.content))
        outcome_error, assertions = _response_result(response, task)
        entry["assertions"] = assertions
        if outcome_error is not None:
            entry["error_kind"] = "assertion" if isinstance(outcome_error, AssertionError) else "http_status"
    entry["response_time_ms"] = (time.monotonic() - clock) * 1000
    entry["error"] = str(outcome_error) if outcome_error is not None else None
    for field in ("step_id", "scenario_id"):
        if task.get(field) is not None:
            entry[field] = task[field]
    return Attempt(entry, outcome_error)


def record_attempt(attempt: Attempt, run) -> None:
    failed = attempt.error is not None
    legacy = test_record_instance.error_record_list if failed else test_record_instance.test_record_list
    legacy.append(attempt.entry)
    record_request(attempt.entry, "failed" if failed else "passed")
    (run.failures if failed else run.successes).append(attempt.entry)


def retry_policy(config: dict) -> AdaptiveRetryPolicy:
    names = {"transient": "transient_budget", "flaky": "flaky_budget", "permanent": "permanent_budget"}
    return AdaptiveRetryPolicy(
        classifier=_classify_native_error, **{names.get(key, key): value for key, value in config.items()}
    )


def _classify_native_error(error: BaseException) -> str:
    import httpx

    if isinstance(error, (httpx.NetworkError, httpx.TimeoutException, httpx.RemoteProtocolError)):
        return "transient"
    return classify_error(error)


async def execute_step(pool: UserClientPool, raw_task: dict, run) -> None:
    # Resolve once, keeping CSV/DB rows and idempotency values stable across retries.
    task = parameter_resolver.resolve(raw_task)
    throttle = task.get("throttle")
    policy = retry_policy(task["retry"]) if "retry" in task else None
    attempt_number = 0
    while not run._worker_stopping():
        if throttle:
            await run.throttle(throttle).acquire()
        async with run.semaphore:
            if run._worker_stopping():
                return
            attempt = await measure(pool, task, run.base_url)
        record_attempt(attempt, run)
        if run._worker_stopping():
            return
        attempt_number += 1
        if attempt.error is None or policy is None:
            break
        decision = policy.decide(attempt.error, attempt_number)
        if not decision.will_retry:
            break
        await asyncio.sleep(decision.delay_seconds)
    if not run._worker_stopping():
        await asyncio.sleep(_think_time_seconds(task.get("think_time")))
