import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("je_action_core.request_context", reason="coordinated ActionCore request-record release")

from je_load_density.engine.asyncio_engine import _send_one, run_async_load
from je_load_density.utils.test_record.run_context import RunContext, use_run_context
from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.wrapper.event.request_hook import request_hook

import httpx
import requests


@pytest.fixture(autouse=True)
def clean_records():
    test_record_instance.clear_records()
    yield
    test_record_instance.clear_records()


def test_falsey_locust_error_response_retains_status_in_both_formats():
    response = requests.Response()
    response.status_code = 500
    response._content = b"down"
    run = RunContext(source="loaddensity", phase="load", engine="locust")
    with use_run_context(run):
        request_hook(100.0, "http://localhost/", "GET", "home", {}, response, ValueError("HTTP 500"), 4, 25)
    assert test_record_instance.error_record_list[0]["status_code"] == "500"
    assert run.snapshot()[0]["status_code"] == 500
    assert run.snapshot()[0]["response_time_ms"] == 25.0


@pytest.mark.parametrize("status,outcome", [(200, "passed"), (500, "failed")])
def test_async_response_captures_canonical_and_legacy_result(status, outcome):
    run = RunContext(source="loaddensity", phase="load", engine="asyncio")

    async def execute():
        transport = httpx.MockTransport(lambda request: httpx.Response(status, content=b"ok"))
        with use_run_context(run):
            async with httpx.AsyncClient(transport=transport) as client:
                await _send_one(client, {"method": "get", "request_url": "http://localhost/"})

    asyncio.run(execute())
    assert run.snapshot()[0]["outcome"] == outcome
    assert run.snapshot()[0]["status_code"] == status
    assert run.snapshot()[0]["response_length"] == 2


def test_async_timeout_records_measured_elapsed_and_nullable_canonical_status(monkeypatch):
    from je_load_density.engine import asyncio_engine

    clock = iter((10.0, 10.025))
    monkeypatch.setattr(asyncio_engine, "time", SimpleNamespace(time=lambda: 100.0, monotonic=lambda: next(clock)))
    run = RunContext(source="loaddensity", phase="load", engine="asyncio")

    async def handle(request):
        await asyncio.sleep(0)
        raise httpx.ReadTimeout("deadline", request=request)

    async def execute():
        with use_run_context(run):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
                await _send_one(client, {"request_url": "http://localhost/"})

    asyncio.run(execute())
    assert test_record_instance.error_record_list[0]["response_time_ms"] == pytest.approx(25.0)
    record = run.snapshot()[0]
    assert record["response_time_ms"] == pytest.approx(25.0)
    assert record["status_code"] is None
    assert record["error"]["kind"] == "timeout"


def test_new_async_run_summary_excludes_old_global_records():
    test_record_instance.test_record_list.append({"name": "old"})
    result = asyncio.run(run_async_load(tasks=[{"request_url": "http://localhost/"}], users=0))
    assert result == {"requests": 0, "failures": 0}


def test_async_run_propagates_explicit_context_to_workers():
    run = RunContext(source="loaddensity", phase="load", engine="asyncio")
    result = asyncio.run(run_async_load(tasks=[{"request_url": "http://127.0.0.1:9/", "timeout": 0.1}],
                                       users=1, duration_seconds=0.2, run_context=run))
    assert result["failures"] >= 1
    assert len(run.snapshot()) == result["failures"]


def test_locust_environment_captures_context_across_greenlet_boundary():
    import gevent
    from locust import HttpUser
    from je_load_density.wrapper.create_locust_env.create_locust_env import create_env

    run = RunContext(source="loaddensity", phase="load", engine="locust")
    env = create_env(HttpUser, run_context=run)
    response = requests.Response()
    response.status_code = 200
    response._content = b"ok"
    try:
        greenlet = gevent.spawn(env.events.request.fire, start_time=100.0, url="http://localhost/",
                               request_type="GET", name="home", context={}, response=response,
                               exception=None, response_length=2, response_time=25.0)
        greenlet.get(timeout=2)
        assert len(run.snapshot()) == 1
        assert run.snapshot()[0]["status_code"] == 200
    finally:
        env.runner.quit()


def test_non_http_locust_event_keeps_protocol_and_unknown_status():
    run = RunContext(source="loaddensity", phase="load", engine="locust")
    with use_run_context(run):
        request_hook(None, "localhost:9000", "TCP", "echo", {}, None, None, 2, 25)
    result = run.snapshot()[0]
    assert result["protocol"] == "tcp"
    assert result["status_code"] is None
    assert result["start_time"] is None
