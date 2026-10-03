"""Native HTTP behavior, session ownership and lifecycle contracts."""

import asyncio

import httpx
import pytest
from je_load_density.engine.entrypoints import start_test

from je_load_density.engine.asyncio_engine import run_async_load
from je_load_density.utils.parameterization import get_resolver, use_resolver
from je_load_density.utils.test_record.test_record_class import test_record_instance


@pytest.fixture
def transport_factory(monkeypatch):
    original = httpx.AsyncClient
    clients = []

    def install(handler):
        def factory(**kwargs):
            client = original(transport=httpx.MockTransport(handler), **kwargs)
            clients.append(client)
            return client

        monkeypatch.setattr(httpx, "AsyncClient", factory)
        return clients

    return install


def test_dispatch_uses_native_http_assertions_and_named_kwargs(transport_factory):
    received = []

    def handler(request):
        received.append(request)
        return httpx.Response(200, json={"ok": True}, headers={"X-State": "ready"})

    clients = transport_factory(handler)
    result = start_test(
        {"user": "http_user"},
        engine="asyncio",
        user_count=1,
        spawn_rate=100,
        test_time=0.08,
        tasks=[
            {
                "method": "post",
                "request_url": "https://local/check",
                "name": "check",
                "params": {"tenant": "one"},
                "json": {"hello": "world"},
                "auth": {"type": "basic", "username": "u", "password": "p"},
                "assertions": [
                    {"type": "json_path", "path": "ok", "value": True},
                    {"type": "header", "name": "X-State", "value": "ready"},
                ],
            }
        ],
    )
    assert result["summary"]["totals"]["successes"] > 0
    assert result["summary"]["per_name"]["check"]["count"] > 0
    assert received[0].url.params["tenant"] == "one"
    assert received[0].headers["Authorization"].startswith("Basic ")
    assert all(client.is_closed for client in clients)


def test_virtual_users_keep_cookie_and_extracted_token_paired(transport_factory):
    issued = []
    checked = []

    def handler(request):
        if request.url.path == "/login":
            token = str(len(issued) + 1)
            issued.append(token)
            return httpx.Response(200, json={"token": token}, headers={"Set-Cookie": f"token={token}; Path=/"})
        checked.append((request.headers["Authorization"], request.headers["Cookie"]))
        return httpx.Response(200)

    transport_factory(handler)
    with use_resolver(get_resolver().fork()):
        result = asyncio.run(
            run_async_load(
                [
                    {
                        "method": "get",
                        "request_url": "https://local/login",
                        "extract": [{"from": "json_path", "path": "token", "var": "token", "scope": "session"}],
                    },
                    {
                        "method": "get",
                        "request_url": "https://local/check",
                        "headers": {"Authorization": "${session.token}"},
                    },
                ],
                users=3,
                duration_seconds=0.08,
            )
        )
    assert result["requests"] > 0
    assert checked
    assert all(cookie == f"token={token}" for token, cookie in checked)


def test_assertion_failure_is_measured_and_retried(transport_factory):
    counter = 0

    def handler(_request):
        nonlocal counter
        counter += 1
        return httpx.Response(200, json={"ok": counter > 1})

    transport_factory(handler)
    result = asyncio.run(
        run_async_load(
            [
                {
                    "method": "get",
                    "request_url": "https://local/check",
                    "assertions": [{"type": "json_path", "path": "ok", "value": True}],
                    "retry": {"flaky": 1, "base_delay": 0, "jitter": 0},
                    "think_time": 0.02,
                }
            ],
            users=1,
            duration_seconds=0.08,
        )
    )
    assert result["failures"] == 1
    assert result["requests"] >= 1
    assert test_record_instance.error_record_list[-1]["status_code"] == "200"


@pytest.mark.parametrize(
    "options",
    [
        {"users": 0},
        {"users": True},
        {"duration_seconds": float("nan")},
        {"max_in_flight": 0},
        {"runner_mode": "master"},
    ],
)
def test_invalid_capabilities_fail_before_opening_clients(transport_factory, options):
    clients = transport_factory(lambda _request: httpx.Response(200))
    run = run_async_load([{"request_url": "https://local", "method": "get"}], **options)
    with pytest.raises((ValueError, TypeError)):
        asyncio.run(run)
    assert clients == []


@pytest.mark.parametrize(
    "task",
    [
        {"assertions": [{"type": "unknown"}]},
        {"extract": [{"from": "unknown", "var": "x"}]},
        {"network_conditioner": {}},
        {"retry": {"transient": -1}},
    ],
)
def test_unsupported_steps_fail_preflight(transport_factory, task):
    clients = transport_factory(lambda _request: httpx.Response(200))
    run = run_async_load([{"method": "get", "request_url": "https://local", **task}])
    with pytest.raises(ValueError):
        asyncio.run(run)
    assert not clients


def test_stop_during_io_closes_clients_without_failure_records(transport_factory):
    from je_load_density.engine.asyncio_engine import AsyncRunHandle

    entered = asyncio.Event()

    async def handler(_request):
        entered.set()
        await asyncio.sleep(30)
        return httpx.Response(200)

    clients = transport_factory(handler)

    async def run():
        handle = AsyncRunHandle([{"method": "get", "request_url": "https://local"}], users=2, duration_seconds=20)
        await handle.start()
        await asyncio.wait_for(entered.wait(), 2)
        handle.stop()
        result = await asyncio.wait_for(handle.wait(), 2)
        assert result["state"] == "cancelled"
        assert result["failures"] == 0
        assert handle.snapshot()["users"] == 0

    asyncio.run(run())
    assert clients
    assert all(client.is_closed for client in clients)


def test_repeated_run_summary_does_not_include_legacy_history(transport_factory):
    transport_factory(lambda _request: httpx.Response(200))
    test_record_instance.error_record_list.append({"response_time_ms": 900, "name": "previous"})
    result = asyncio.run(
        run_async_load([{"request_url": "https://local", "method": "get"}], users=1, duration_seconds=0.03)
    )
    assert result["summary"]["totals"]["failures"] == 0
    assert "previous" not in result["summary"]["per_name"]


def test_completed_worker_error_is_observed_before_forced_deadline(monkeypatch):
    from je_load_density.engine.asyncio_engine import AsyncRunHandle

    async def run():
        entered = asyncio.Event()
        handle = AsyncRunHandle([{"method": "get", "url": "https://local"}], users=1, duration_seconds=60)
        resize = handle._resize

        async def failed_user(_httpx, _resolver):
            entered.set()
            raise RuntimeError("worker failed at deadline")

        async def resize_at_deadline(httpx_module, count, available):
            await resize(httpx_module, count, available)
            await entered.wait()
            await asyncio.sleep(0)
            handle.duration = 0

        monkeypatch.setattr(handle, "_user", failed_user)
        monkeypatch.setattr(handle, "_resize", resize_at_deadline)
        await handle.start()
        with pytest.raises(RuntimeError, match="worker failed at deadline"):
            await handle.wait()
        assert entered.is_set()
        assert handle.state == "failed"
        assert all(worker.done() for worker in handle.workers)

    asyncio.run(run())


def test_worker_failure_at_run_deadline_propagates(transport_factory):
    transport_factory(lambda _request: (_ for _ in ()).throw(ValueError("invalid transport")))
    run = run_async_load([{"request_url": "https://local"}], users=1, duration_seconds=0.005)
    with pytest.raises(ValueError, match="invalid transport"):
        asyncio.run(run)


def test_expected_error_status_can_pass_assertions(transport_factory):
    transport_factory(lambda _request: httpx.Response(404, text="missing"))
    result = asyncio.run(
        run_async_load(
            [
                {
                    "request_url": "https://local",
                    "assertions": [{"type": "status_code", "value": 404}],
                }
            ],
            users=1,
            duration_seconds=0.03,
        )
    )
    assert result["requests"] > 0
    assert result["failures"] == 0


def test_httpx_connection_failure_uses_transient_retry_budget(transport_factory):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200)

    transport_factory(handler)
    result = asyncio.run(
        run_async_load(
            [
                {
                    "request_url": "https://local",
                    "retry": {"transient": 1, "base_delay": 0, "jitter": 0},
                    "think_time": 30,
                }
            ],
            users=1,
            duration_seconds=0.05,
        )
    )
    assert result["failures"] == 1
    assert result["requests"] == 1


@pytest.mark.parametrize(
    "task",
    [
        {"headers": 7},
        {"run_if": {"unsupported": True}},
        {"think_time": {"minimum": 1}},
        {"auth": {"type": "basic", "usernmae": "u"}},
    ],
)
def test_static_invalid_second_step_fails_before_any_io(transport_factory, task):
    clients = transport_factory(lambda _request: httpx.Response(200))
    run = run_async_load(
        [{"request_url": "https://local"}, {"request_url": "https://local", **task}],
        users=1,
        duration_seconds=0.03,
    )
    with pytest.raises(ValueError):
        asyncio.run(run)
    assert clients == []


@pytest.mark.parametrize("additional_options", [{}, {"verify": "${verify_tls}"}])
def test_invalid_static_transport_fails_before_earlier_step_io(transport_factory, monkeypatch, additional_options):
    received = []
    clients = transport_factory(lambda request: received.append(request) or httpx.Response(200))
    original = httpx.AsyncClient

    def client(**options):
        if options.get("cert") == "invalid.pem":
            raise ValueError("invalid certificate configuration")
        return original(**options)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    run = run_async_load(
        [{"request_url": "https://local"},
         {"request_url": "https://local", "cert": "invalid.pem", **additional_options}],
        users=1,
        duration_seconds=0.1,
        variables={"verify_tls": False},
    )
    with pytest.raises(ValueError, match="invalid certificate"):
        asyncio.run(run)
    assert received == []
    assert all(client.is_closed for client in clients)


def test_unknown_shape_option_fails_before_any_io(transport_factory):
    clients = transport_factory(lambda _request: httpx.Response(200))
    run = run_async_load(
        [{"request_url": "https://local"}],
        users=1,
        duration_seconds=0.03,
        load_shape="spike",
        shape_config={"baseline_users": 1, "spwan_rate": 100},
    )
    with pytest.raises(ValueError):
        asyncio.run(run)
    assert clients == []


@pytest.mark.parametrize("limit,expected", [(None, 3), (1, 1)])
def test_shape_concurrency_uses_peak_users_unless_explicitly_limited(transport_factory, limit, expected):
    active = peak = 0

    async def handler(_request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0.04)
            return httpx.Response(200)
        finally:
            active -= 1

    transport_factory(handler)
    asyncio.run(
        run_async_load(
            [{"request_url": "https://local"}],
            users=1,
            duration_seconds=0.12,
            load_shape="stages",
            shape_config={"stages": [{"duration": 1, "users": 3, "spawn_rate": 1000}]},
            max_in_flight=limit,
        )
    )
    assert peak == expected
    assert active == 0


def test_certificate_clients_do_not_mutate_shared_trust_context(transport_factory):
    import ssl

    from je_load_density.engine.async_http import UserClientPool

    seen = []

    class Client:
        def __init__(self, **kwargs):
            seen.append(kwargs)
            self.cookies = httpx.Cookies()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    async def run():
        trust = ssl.create_default_context()
        module = type("Http", (), {"Cookies": httpx.Cookies, "AsyncClient": Client})
        async with UserClientPool(module, False, trust) as pool:
            await pool.client({"cert": "one.pem"})
            await pool.client({"client_cert": "two.pem"})
            await pool.client({})
        assert seen[0]["verify"] is not trust
        assert seen[1]["verify"] is not trust
        assert seen[2]["verify"] is trust

    asyncio.run(run())


@pytest.mark.parametrize("operation", ["stop", "scale_down"])
def test_worker_cleanup_error_propagates_on_stop_and_scale_down(operation):
    from je_load_density.engine.asyncio_engine import AsyncRunHandle

    async def run():
        entered = asyncio.Event()
        handle = AsyncRunHandle([{"request_url": "https://local"}], users=1, duration_seconds=20)

        async def user(_httpx, _resolver):
            entered.set()
            try:
                await asyncio.sleep(30)
            finally:
                raise RuntimeError("client cleanup failed")

        handle._user = user
        await handle.start()
        await asyncio.wait_for(entered.wait(), 2)
        try:
            if operation == "scale_down":
                with pytest.raises(RuntimeError, match="client cleanup failed"):
                    await handle._resize(None, 0, 0)
            handle.stop()
            with pytest.raises(RuntimeError, match="client cleanup failed"):
                await handle.wait()
        finally:
            if not handle._task.done():
                handle.stop()
                await asyncio.gather(handle._task, return_exceptions=True)

    asyncio.run(run())


def test_cancellation_during_start_closes_owned_run_and_clients(transport_factory, monkeypatch):
    from je_load_density.engine import asyncio_engine

    clients = transport_factory(lambda _request: httpx.Response(200))
    handles = []

    class TrackedHandle(asyncio_engine.AsyncRunHandle):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            handles.append(self)

    monkeypatch.setattr(asyncio_engine, "AsyncRunHandle", TrackedHandle)

    async def run():
        caller = asyncio.create_task(
            asyncio_engine.run_async_load([{"request_url": "https://local"}], duration_seconds=20)
        )
        asyncio.get_running_loop().call_soon(caller.cancel)
        with pytest.raises(asyncio.CancelledError):
            await caller
        assert len(handles) == 1
        assert handles[0]._task.done()
        assert handles[0].state == "cancelled"
        assert all(worker.done() for worker in handles[0].workers)
        assert clients
        assert all(client.is_closed for client in clients)

    asyncio.run(run())


@pytest.mark.parametrize("status", [200, 503])
def test_deadline_stops_steps_and_retries_after_transport_swallows_cancel(transport_factory, status):
    from je_load_density.engine.asyncio_engine import AsyncRunHandle

    calls = []

    async def handler(request):
        calls.append(request.url.path)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            if len(calls) != 1:
                raise
        return httpx.Response(status)

    clients = transport_factory(handler)

    async def run():
        handle = AsyncRunHandle([
            {"request_url": "https://local/first", "think_time": 30,
             "retry": {"permanent": 2, "base_delay": 30, "jitter": 0}},
            {"request_url": "https://local/next"},
        ], users=1, duration_seconds=0.05)
        await handle.start()
        result = await asyncio.wait_for(handle.wait(), 1)
        assert result["state"] == "completed"
        assert calls == ["/first"]
        assert all(worker.done() for worker in handle.workers)

    asyncio.run(run())
    assert clients
    assert all(client.is_closed for client in clients)


def test_shrinking_load_stops_only_retiring_worker_when_transport_swallows_cancel(transport_factory, monkeypatch):
    from je_load_density.engine.asyncio_engine import AsyncRunHandle

    entered = asyncio.Event()
    counts = {}

    async def handler(_request):
        worker = asyncio.current_task()
        counts[worker] = counts.get(worker, 0) + 1
        if len(counts) == 2:
            entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            if counts[worker] != 1:
                raise
        return httpx.Response(200)

    clients = transport_factory(handler)

    async def run():
        handle = AsyncRunHandle([{"request_url": "https://local"}], users=2, duration_seconds=20)

        async def schedule(httpx_module):
            await handle._resize(httpx_module, 2, 2)
            await handle._stop.wait()

        monkeypatch.setattr(handle, "_schedule", schedule)
        await handle.start()
        try:
            await asyncio.wait_for(entered.wait(), 1)
            survivor, retiring = handle.workers
            await asyncio.wait_for(handle._resize(None, 1, 0), 1)
            assert retiring.done()
            assert not survivor.done()
            assert not handle._stop.is_set()
            assert counts[retiring] == 1
        finally:
            handle.stop()
            await asyncio.wait_for(handle.wait(), 1)

    asyncio.run(run())
    assert clients
    assert all(client.is_closed for client in clients)
