"""Parameter state follows an explicit user while data rows remain shared."""

import asyncio
import subprocess
import sys
from contextlib import contextmanager
from types import SimpleNamespace

import gevent
import pytest

from je_load_density.utils import parameterization as parameters
from je_load_density.utils.parameterization import (
    ParameterResolver,
    parameter_resolver,
    register_variable,
)
from je_load_density.wrapper.user_template.request_executor import _apply_extractors


@pytest.fixture(autouse=True)
def isolated_default():
    parameter_resolver.clear()
    yield
    parameter_resolver.clear()


def test_fork_detaches_nested_variable_values_and_future_registration():
    base = ParameterResolver()
    nested = {"roles": ["reader"]}
    base.register_variable("claims", nested)
    first, second = base.fork(), base.fork()
    nested["roles"].append("admin")
    first.register_variable("claims", {"roles": ["writer"]})
    assert first.resolve("${var.claims}") == "{'roles': ['writer']}"
    assert second.resolve("${var.claims}") == "{'roles': ['reader']}"
    assert base.resolve("${var.claims}") == "{'roles': ['reader', 'admin']}"


def test_scoped_facade_restores_nested_context_and_keeps_default_state():
    def fail_in_scope(resolver):
        with parameters.use_resolver(resolver):
            register_variable("token", "second")
            assert parameters.resolve("${token}") == "second"
            raise RuntimeError("scope failed")

    register_variable("token", "default")
    first, second = parameter_resolver.fork(), parameter_resolver.fork()
    saved_resolve = parameter_resolver.resolve
    with parameters.use_resolver(first):
        register_variable("token", "first")
        assert saved_resolve("${var.token}") == "first"
        with pytest.raises(RuntimeError):
            fail_in_scope(second)
        assert parameters.get_resolver() is first
        assert parameters.resolve("${token}") == "first"
    assert saved_resolve("${token}") == "default"


def test_async_users_keep_interleaved_extractions_local():
    async def user(token):
        local = parameter_resolver.fork()
        with parameters.use_resolver(local):
            _apply_extractors(SimpleNamespace(json=lambda: {"token": token}),
                              [{"var": "token", "path": "token"}])
            await asyncio.sleep(0)
            return parameter_resolver.resolve({"Authorization": "Bearer ${var.token}"})

    async def execute():
        return await asyncio.gather(user("first"), user("second"))

    assert asyncio.run(execute()) == [{"Authorization": "Bearer first"}, {"Authorization": "Bearer second"}]
    assert parameter_resolver.resolve("${var.token}") == "${var.token}"


def test_greenlet_scopes_restore_and_do_not_share_tokens():
    def user(token):
        with parameters.use_resolver(parameter_resolver.fork()):
            register_variable("token", token)
            gevent.sleep(0)
            return parameters.resolve("${var.token}")

    users = [gevent.spawn(user, token) for token in ("first", "second")]
    assert [user.get() for user in users] == ["first", "second"]
    assert parameters.resolve("${var.token}") == "${var.token}"


def test_session_extraction_is_distinct_and_user_local():
    register_variable("token", "base")
    first, second = parameter_resolver.fork(), parameter_resolver.fork()
    with parameters.use_resolver(first):
        _apply_extractors(SimpleNamespace(json=lambda: {"token": "session-first"}),
                          [{"var": "token", "path": "token", "scope": "session"}])
        assert parameters.resolve("${session.token}/${var.token}") == "session-first/base"
    with parameters.use_resolver(second):
        assert parameters.resolve("${session.token}/${var.token}") == "${session.token}/base"


def test_csv_request_fields_reuse_one_row_and_forks_share_provider(tmp_path):
    path = tmp_path / "users.csv"
    path.write_text("user,password\nalice,alice-secret\nbob,bob-secret\n", encoding="utf-8")
    base = ParameterResolver()
    base.register_csv_source("accounts", str(path), cycle=False)
    first, second = base.fork(), base.fork()
    task = {"url": "https://example.test/${csv.accounts.user}",
            "json": {"user": "${csv.accounts.user}", "password": "${csv.accounts.password}"}}
    assert first.resolve(task) == {"url": "https://example.test/alice",
                                   "json": {"user": "alice", "password": "alice-secret"}}
    assert second.resolve(task) == {"url": "https://example.test/bob",
                                    "json": {"user": "bob", "password": "bob-secret"}}
    assert base.resolve(task) == task


def test_db_request_fields_reuse_one_row_across_nested_collections(monkeypatch):
    monkeypatch.setattr(ParameterResolver, "_read_db", staticmethod(lambda *_args: [
        {"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]))
    base = ParameterResolver()
    base.register_db_source("accounts", "sqlite://", "SELECT id, name FROM accounts")
    task = ("${db.accounts.id}", [{"name": "${db.accounts.name}"}])
    assert base.fork().resolve(task) == ("1", [{"name": "Alice"}])
    assert base.fork().resolve(task) == ("2", [{"name": "Bob"}])
    assert base.resolve(task) == ("1", [{"name": "Alice"}])


def test_source_registration_and_clear_within_scope_do_not_change_base(tmp_path):
    path = tmp_path / "accounts.csv"
    path.write_text("name\nAlice\n", encoding="utf-8")
    register_variable("token", "base")
    with parameters.use_resolver(parameter_resolver.fork()):
        parameters.register_csv_source("local", str(path))
        assert parameters.resolve("${csv.local.name}") == "Alice"
        parameter_resolver.clear()
        assert parameters.resolve("${token}") == "${token}"
    assert parameters.resolve("${token}") == "base"
    assert parameters.resolve("${csv.local.name}") == "${csv.local.name}"


class _LocustHttpResponse:
    status_code, text, content = 200, "ok", b"ok"

    def __init__(self, token):
        self.token = token

    def json(self):
        return {"token": self.token}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        gevent.sleep(0)

    def success(self):
        pass

    def failure(self, reason):
        pytest.fail(reason)


def _setup_locust_http_users(monkeypatch, backend):
    from locust.env import Environment

    from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
    from je_load_density.wrapper.user_template import (
        async_http_user_template as async_template,
    )
    from je_load_density.wrapper.user_template import (
        fast_http_user_template as fast_template,
    )
    from je_load_density.wrapper.user_template import (
        http_user_template as http_template,
    )

    templates = {"http": (http_template.HttpUserWrapper, "http_user"),
                 "fast_http": (fast_template.FastHttpUserWrapper, "fast_http_user"),
                 "async_http": (async_template.AsyncHttpUserWrapper, "async_http_user")}
    user_type, proxy_name = templates[backend]
    login = {"method": "get", "url": "/login", "extract": [{"var": "token", "path": "token"}]}
    request = {"method": "get", "url": "/data", "headers": {"Authorization": "Bearer ${token}"}}
    proxy = SimpleNamespace(tasks=[login, request])
    monkeypatch.setitem(locust_wrapper_proxy.user_dict, proxy_name, proxy)
    env = Environment()
    env.events.request.add_listener(lambda **_kwargs: gevent.sleep(0))

    users, calls = [], {"first": [], "second": []}
    for token in calls:
        user = user_type(env)

        def get(url, _token=token, **kwargs):
            if url == "/data":
                calls[_token].append(kwargs["headers"]["Authorization"])
            return _LocustHttpResponse(_token)

        if backend == "async_http":
            user._client = SimpleNamespace(request=lambda _method, url, _get=get, **kwargs: _get(url, **kwargs))
        else:
            user.method = {"get": get}
        users.append(user)
    return users, calls, proxy, request


@pytest.mark.parametrize("backend", ["http", "fast_http", "async_http"])
def test_locust_http_users_keep_extracted_tokens_across_scenario_calls(monkeypatch, backend):
    users, calls, proxy, request = _setup_locust_http_users(monkeypatch, backend)
    invoke = (lambda user: user.run_tasks()) if backend == "async_http" else (lambda user: user.test())
    gevent.joinall([gevent.spawn(invoke, user) for user in users], raise_error=True)
    proxy.tasks = [request]
    gevent.joinall([gevent.spawn(invoke, user) for user in users], raise_error=True)
    assert calls == {"first": ["Bearer first", "Bearer first"], "second": ["Bearer second", "Bearer second"]}
    assert parameters.resolve("${token}") == "${token}"


@pytest.mark.parametrize("module_name,setter,proxy_name", [
    ("http_user_template", "set_wrapper_http_user", "http_user"),
    ("fast_http_user_template", "set_wrapper_fasthttp_user", "fast_http_user"),
    ("async_http_user_template", "set_wrapper_async_http_user", "async_http_user"),
])
def test_http_template_setup_registers_database_sources(monkeypatch, module_name, setter, proxy_name):
    import importlib

    from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy

    # Security audit: Module suffix comes only from the three literal pytest parameter cases above.
    # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
    module = importlib.import_module(f"je_load_density.wrapper.user_template.{module_name}")
    monkeypatch.setattr(ParameterResolver, "_read_db", staticmethod(lambda *_args: [{"name": "Alice"}]))
    monkeypatch.setitem(locust_wrapper_proxy.user_dict, proxy_name, SimpleNamespace(configure=lambda *_a, **_k: None))
    getattr(module, setter)({}, db_sources=[{"name": "accounts", "connection_string": "sqlite://",
                                            "query": "SELECT name FROM accounts"}])
    assert parameters.resolve("${db.accounts.name}") == "Alice"


def test_shared_provider_assigns_complete_rows_once_across_concurrent_users(tmp_path):
    path = tmp_path / "accounts.csv"
    path.write_text("id,secret\n" + "".join(f"{index},secret-{index}\n" for index in range(64)), encoding="utf-8")
    base = ParameterResolver()
    base.register_csv_source("accounts", str(path), cycle=False)

    def resolve_user(local):
        with parameters.use_resolver(local):
            gevent.sleep(0)
            return parameters.resolve({"id": "${csv.accounts.id}", "secret": "${csv.accounts.secret}"})

    users = [gevent.spawn(resolve_user, base.fork()) for _index in range(64)]
    rows = [user.get() for user in users]
    assert {row["id"] for row in rows} == {str(index) for index in range(64)}
    assert all(row["secret"] == f"secret-{row['id']}" for row in rows)
    assert base.resolve("${csv.accounts.id}") == "${csv.accounts.id}"


def test_cancelled_async_scope_restores_parent_selection():
    parent, child = ParameterResolver(), ParameterResolver()
    parent.register_variable("token", "parent")

    async def execute():
        entered = asyncio.Event()

        async def user():
            with parameters.use_resolver(child):
                register_variable("token", "child")
                entered.set()
                await asyncio.Event().wait()

        with parameters.use_resolver(parent):
            task = asyncio.create_task(user())
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert parameters.get_resolver() is parent
            assert parameters.resolve("${token}") == "parent"

    asyncio.run(execute())
    assert parameters.resolve("${token}") == "${token}"


@pytest.mark.parametrize("fail_query", [False, True])
def test_database_source_closes_connection_and_disposes_pool_after_cache(monkeypatch, fail_query):
    closed = []
    result = SimpleNamespace(keys=lambda: ["name"], fetchall=lambda: [("Alice",)])

    def execute(_query):
        if fail_query:
            raise ValueError("query failed")
        return result

    @contextmanager
    def connect():
        try:
            yield SimpleNamespace(execute=execute)
        finally:
            closed.append("connection")

    engine = SimpleNamespace(connect=connect, dispose=lambda: closed.append("pool"))
    monkeypatch.setitem(sys.modules, "sqlalchemy", SimpleNamespace(create_engine=lambda *_a, **_k: engine,
                                                                   text=lambda query: query))
    base = ParameterResolver()
    if fail_query:
        with pytest.raises(ValueError, match="query failed"):
            base.register_db_source("accounts", "sqlite://", "SELECT name")
    else:
        base.register_db_source("accounts", "sqlite://", "SELECT name")
        assert base.fork().resolve("${db.accounts.name}") == "Alice"
    assert closed == ["connection", "pool"]


def test_cookie_jars_created_before_locust_patch_remain_user_local():
    script = """
from je_load_density.utils.scenario.cookie_jar import jar_for_user
parent = jar_for_user()
import locust
import threading
seen = []
thread = threading.Thread(target=lambda: seen.append(jar_for_user()))
thread.start()
thread.join()
assert seen[0] is not jar_for_user()
"""
    # Security audit: Current interpreter executes the fixed test program without a shell.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stderr


def test_async_cookie_jars_do_not_inherit_parent_or_sibling_state():
    from je_load_density.utils.scenario.cookie_jar import jar_for_user

    async def execute():
        parent = jar_for_user()

        async def user():
            first = jar_for_user()
            await asyncio.sleep(0)
            assert jar_for_user() is first
            return first

        first, second = await asyncio.gather(user(), user())
        assert first is not parent
        assert second is not parent
        assert first is not second
        assert jar_for_user() is parent

    asyncio.run(execute())


def test_parameter_only_import_leaves_locust_and_gevent_unloaded():
    script = """
import sys
from je_load_density.utils.parameterization import ParameterResolver, use_resolver, resolve
with use_resolver(ParameterResolver()):
    assert resolve('plain') == 'plain'
assert 'locust' not in sys.modules
assert 'gevent' not in sys.modules
"""
    # Security audit: Fixed parameter-import regression program runs in the current interpreter without a shell.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stderr


def test_native_threads_keep_local_tokens_and_allocate_shared_rows(tmp_path):
    path = tmp_path / "accounts.csv"
    path.write_text("id,secret\n" + "".join(f"{index},secret-{index}\n" for index in range(64)), encoding="utf-8")
    script = """
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from je_load_density.utils.parameterization import ParameterResolver, use_resolver, resolve, register_variable
base = ParameterResolver()
base.register_csv_source('accounts', sys.argv[1], cycle=False)
register_variable('token', 'default')
barrier = threading.Barrier(8)
def user(index):
    with use_resolver(base.fork()):
        register_variable('token', f'user-{index}')
        barrier.wait(timeout=10)
        row = resolve({'id': '${csv.accounts.id}', 'secret': '${csv.accounts.secret}', 'token': '${token}'})
        assert row['token'] == f'user-{index}'
        assert row['secret'] == f"secret-{row['id']}"
        return row['id']
with ThreadPoolExecutor(max_workers=8) as pool:
    ids = list(pool.map(user, range(64)))
assert set(ids) == {str(index) for index in range(64)}
assert resolve('${token}') == 'default'
assert 'locust' not in sys.modules
assert 'gevent' not in sys.modules
"""
    # Security audit: Fixed test program reads the temporary action path from sys.argv; no Python/shell interpolation.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
    completed = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stderr
