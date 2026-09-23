"""
``_common.new_template_event_loop`` and ``run_template_coroutine``.

Under Locust, gevent turns the event loop's thread-pool threads into greenlets, which never run
on Windows while the loop waits; a host name lookup through the pool then never returns. The
template loop resolves in the calling thread, so the pool is not touched. The tests give the loop
a pool that refuses work: with a plain loop they fail instead of hanging.
"""

import asyncio
import concurrent.futures
import socket

import pytest

from je_load_density.wrapper.user_template._common import new_template_event_loop, run_template_coroutine


class RefusingExecutor(concurrent.futures.ThreadPoolExecutor):
    def submit(self, fn, /, *_args, **_kwargs):
        raise AssertionError(f"the event loop's thread pool was used for {fn!r}")


@pytest.fixture
def listening_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        yield server.getsockname()[1]


async def open_and_close(host, port):
    _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), 5)
    writer.close()
    await writer.wait_closed()
    return "connected"


def test_host_name_lookup_does_not_use_the_thread_pool(listening_port):
    loop = new_template_event_loop()
    loop.set_default_executor(RefusingExecutor())
    try:
        result = loop.run_until_complete(open_and_close("localhost", listening_port))
    finally:
        loop.close()

    assert result == "connected"  # nosec B101


def test_plain_loop_would_use_the_thread_pool(listening_port):
    loop = asyncio.new_event_loop()
    loop.set_default_executor(RefusingExecutor())
    try:
        with pytest.raises(AssertionError, match="thread pool"):
            loop.run_until_complete(open_and_close("localhost", listening_port))
    finally:
        loop.close()


def test_run_template_coroutine_returns_the_result_and_cancels_leftover_tasks():
    leftovers = []

    async def spawn_and_return():
        leftovers.append(asyncio.get_running_loop().create_task(asyncio.sleep(60)))
        return 7

    assert run_template_coroutine(spawn_and_return()) == 7  # nosec B101
    assert leftovers[0].cancelled()  # nosec B101


def test_run_template_coroutine_raises_the_coroutine_error():
    async def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run_template_coroutine(fail())
