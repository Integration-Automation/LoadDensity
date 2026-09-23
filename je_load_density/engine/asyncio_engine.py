"""
Native asyncio load engine.

Independent of Locust / gevent — uses stdlib ``asyncio`` and ``httpx``
(lazy) to drive HTTP load. Writes results into the same
``test_record_instance`` so reports, SLA gates, and persistence behave
identically.

Usage::

    import asyncio
    from je_load_density.engine.asyncio_engine import run_async_load

    asyncio.run(run_async_load(
        tasks=[{"method": "get", "request_url": "https://x"}],
        users=50, duration_seconds=30,
    ))
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.utils.test_record.test_record_class import test_record_instance


def _import_httpx():
    try:
        import httpx
    except ImportError as error:
        raise RuntimeError(
            "httpx is required for the asyncio engine; "
            "install with: pip install 'httpx[http2]'"
        ) from error
    return httpx


def _record(method: str, url: str, status: int, elapsed_ms: float, length: int, started: float) -> None:
    """Record one response. A 4xx/5xx is a failure, as Locust's HTTP users count it, so SLA gates
    and failure-rate reports mean the same thing whichever engine produced the records."""
    entry = {
        "Method": method.upper(),
        "test_url": url,
        "name": url,
        "status_code": str(status),
        "response_time_ms": elapsed_ms,
        "response_length": length,
        "start_time": started,
    }
    if status >= 400:
        entry["error"] = f"HTTP {status}"
        test_record_instance.error_record_list.append(entry)
        return
    entry["error"] = None
    test_record_instance.test_record_list.append(entry)


def _record_error(method: str, url: str, error: str, started: float) -> None:
    test_record_instance.error_record_list.append({
        "Method": method.upper(),
        "test_url": url,
        "name": url,
        "status_code": "0",
        "response_time_ms": 0.0,
        "response_length": 0,
        "error": error,
        "start_time": started,
    })


async def _send_one(client, raw_task: Dict[str, Any]) -> None:
    task = parameter_resolver.resolve(raw_task)
    method = str(task.get("method", "get")).lower()
    url = task["request_url"]
    headers = task.get("headers") or None
    body = task.get("json")
    started = time.time()
    start = time.monotonic()
    try:
        response = await client.request(
            method.upper(), url, headers=headers, json=body,
            timeout=float(task.get("timeout", 10.0)),
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        _record(method, url, response.status_code, elapsed_ms, len(response.content), started)
    except Exception as error:  # noqa: BLE001
        _record_error(method, url, repr(error), started)


async def _worker(
    client,
    tasks: List[Dict[str, Any]],
    deadline: float,
    semaphore: asyncio.Semaphore,
) -> None:
    while time.monotonic() < deadline:
        for task in tasks:
            if time.monotonic() >= deadline:
                return
            async with semaphore:
                await _send_one(client, task)


async def run_async_load(
    tasks: List[Dict[str, Any]],
    users: int = 10,
    duration_seconds: float = 10.0,
    http2: bool = False,
    max_in_flight: Optional[int] = None,
) -> Dict[str, Any]:
    """Run a pure-asyncio HTTP load test. Returns a summary dict."""
    httpx = _import_httpx()
    semaphore = asyncio.Semaphore(max_in_flight or max(users, 1))
    async with httpx.AsyncClient(http2=http2) as client:
        # Start the clock once the client exists, so duration_seconds is time under load and a
        # slow client setup cannot eat a short run's whole budget.
        deadline = time.monotonic() + duration_seconds
        workers = [
            asyncio.create_task(_worker(client, tasks, deadline, semaphore))
            for _ in range(users)
        ]
        await asyncio.gather(*workers, return_exceptions=True)
    load_density_logger.info(
        f"asyncio engine done — {len(test_record_instance.test_record_list)} ok, "
        f"{len(test_record_instance.error_record_list)} err"
    )
    return {
        "requests": len(test_record_instance.test_record_list),
        "failures": len(test_record_instance.error_record_list),
    }
