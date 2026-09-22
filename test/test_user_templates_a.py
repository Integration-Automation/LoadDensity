"""
Unit tests for the protocol user templates: amqp, apns, async_http, cassandra,
coap, consul, couchbase, elasticsearch, etcd, fcm, ftp, fuzz_http, graphql_ws
and grpc.

Client libraries are replaced by in-memory fakes; no network or broker is used.
"""

import json
import sys
import types
import urllib.error
import urllib.request
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template import amqp_user_template as amqp_t
from je_load_density.wrapper.user_template import apns_user_template as apns_t
from je_load_density.wrapper.user_template import async_http_user_template as async_http_t
from je_load_density.wrapper.user_template import cassandra_user_template as cassandra_t
from je_load_density.wrapper.user_template import coap_user_template as coap_t
from je_load_density.wrapper.user_template import consul_user_template as consul_t
from je_load_density.wrapper.user_template import couchbase_user_template as couchbase_t
from je_load_density.wrapper.user_template import elasticsearch_user_template as es_t
from je_load_density.wrapper.user_template import etcd_user_template as etcd_t
from je_load_density.wrapper.user_template import fcm_user_template as fcm_t
from je_load_density.wrapper.user_template import ftp_user_template as ftp_t
from je_load_density.wrapper.user_template import fuzz_http_user_template as fuzz_t
from je_load_density.wrapper.user_template import graphql_ws_user_template as gql_ws_t
from je_load_density.wrapper.user_template import grpc_user_template as grpc_t


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class FakeEnvironment:
    """Locust environment stand-in whose request event records every fire() call."""

    def __init__(self) -> None:
        self.fired: List[Dict[str, Any]] = []
        self.events = SimpleNamespace(request=SimpleNamespace(fire=self._record))

    def _record(self, **kwargs: Any) -> None:
        self.fired.append(kwargs)


def single_event(env: FakeEnvironment, request_type: str, name: str) -> Dict[str, Any]:
    assert len(env.fired) == 1, env.fired
    event = env.fired[0]
    assert event["request_type"] == request_type
    assert event["name"] == name
    assert event["response_time"] >= 0
    return event


def assert_success(env: FakeEnvironment, request_type: str, name: str,
                   length: Optional[int] = None) -> Dict[str, Any]:
    event = single_event(env, request_type, name)
    assert event["exception"] is None
    if length is not None:
        assert event["response_length"] == length
    return event


def assert_failure(env: FakeEnvironment, request_type: str, name: str,
                   exc_type: type, match: str = "") -> BaseException:
    event = single_event(env, request_type, name)
    error = event["exception"]
    assert isinstance(error, exc_type), repr(error)
    assert match in str(error)
    assert event["response_length"] == 0
    return error


def make_module(name: str, **attrs: Any) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def block_import(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    """Make ``import <name>`` raise ImportError for every given module name."""
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)


def fresh_proxy(monkeypatch: pytest.MonkeyPatch, key: str) -> Any:
    """Swap the global proxy for ``key`` with a new instance for the test's duration."""
    fresh = type(locust_wrapper_proxy.user_dict[key])()
    monkeypatch.setitem(locust_wrapper_proxy.user_dict, key, fresh)
    return fresh


class FakeHttpResponse:
    """Context-manager response as returned by ``urllib.request.urlopen``."""

    def __init__(self, body: bytes = b"") -> None:
        self._body = body

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *exc_info: Any) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def patch_urlopen(monkeypatch: pytest.MonkeyPatch, body: bytes = b"",
                  error: Optional[BaseException] = None) -> List[Dict[str, Any]]:
    """Replace urlopen; return the list that collects each (request, timeout) call."""
    calls: List[Dict[str, Any]] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeHttpResponse:
        calls.append({"request": request, "timeout": timeout})
        if error is not None:
            raise error
        return FakeHttpResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


@pytest.fixture(autouse=True)
def isolated_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parameter_resolver, "_variables", {})
    monkeypatch.setattr(parameter_resolver, "_csv_sources", {})


@pytest.fixture
def env() -> FakeEnvironment:
    return FakeEnvironment()


# ---------------------------------------------------------------------------
# set_wrapper_* and run_tasks, shared across all fourteen templates
# ---------------------------------------------------------------------------

SETTER_CASES = [
    ("amqp_user", amqp_t.set_wrapper_amqp_user, amqp_t.AmqpUserWrapper,
     {"connection": {"url": "amqp://broker"}}),
    ("apns_user", apns_t.set_wrapper_apns_user, apns_t.ApnsUserWrapper,
     {"connection": {"endpoint": "https://apns"}}),
    ("async_http_user", async_http_t.set_wrapper_async_http_user, async_http_t.AsyncHttpUserWrapper,
     {"host": "http://svc", "http2": True}),
    ("cassandra_user", cassandra_t.set_wrapper_cassandra_user, cassandra_t.CassandraUserWrapper,
     {"contact_points": ["10.0.0.1"], "keyspace": "ks"}),
    ("coap_user", coap_t.set_wrapper_coap_user, coap_t.CoapUserWrapper,
     {"connection": {"uri": "coap://dev"}}),
    ("consul_user", consul_t.set_wrapper_consul_user, consul_t.ConsulUserWrapper,
     {"connection": {"addr": "http://consul:8500"}}),
    ("couchbase_user", couchbase_t.set_wrapper_couchbase_user, couchbase_t.CouchbaseUserWrapper,
     {"connection": {"bucket": "b"}}),
    ("elasticsearch_user", es_t.set_wrapper_elasticsearch_user, es_t.ElasticsearchUserWrapper,
     {"connection": {"hosts": ["http://es:9200"]}}),
    ("etcd_user", etcd_t.set_wrapper_etcd_user, etcd_t.EtcdUserWrapper,
     {"connection": {"host": "etcd"}}),
    ("fcm_user", fcm_t.set_wrapper_fcm_user, fcm_t.FcmUserWrapper,
     {"connection": {"project_id": "p"}}),
    ("ftp_user", ftp_t.set_wrapper_ftp_user, ftp_t.FtpUserWrapper,
     {"connection": {"host": "ftp"}}),
    ("fuzz_http_user", fuzz_t.set_wrapper_fuzz_http_user, fuzz_t.FuzzHttpUserWrapper,
     {"connection": {"base": "http://x"}}),
    ("graphql_ws_user", gql_ws_t.set_wrapper_graphql_ws_user, gql_ws_t.GraphQLWebSocketUserWrapper,
     {"connection": {"url": "wss://gql"}}),
    ("grpc_user", grpc_t.set_wrapper_grpc_user, grpc_t.GrpcUserWrapper,
     {"host": "grpc:50051"}),
]
SETTER_IDS = [case[0] for case in SETTER_CASES]


@pytest.mark.parametrize("key, setter, user_cls, specific", SETTER_CASES, ids=SETTER_IDS)
def test_setter_configures_proxy_and_returns_wrapper(monkeypatch, key, setter, user_cls, specific):
    proxy = fresh_proxy(monkeypatch, key)
    tasks = [{"method": "noop"}]
    detail = {"user": key}
    returned = setter(detail, tasks=tasks, variables={"token": "abc"}, rate=3, **specific)
    assert returned is user_cls
    assert proxy.user_detail_dict == detail
    assert proxy.tasks == tasks
    for attr, value in specific.items():
        assert getattr(proxy, attr) == value
    assert proxy.extra == {"rate": 3}


@pytest.mark.parametrize("key, setter, user_cls, specific", SETTER_CASES, ids=SETTER_IDS)
def test_setter_registers_variables_and_csv_sources(monkeypatch, tmp_path, key, setter, user_cls, specific):
    fresh_proxy(monkeypatch, key)
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("login\nalice\nbob\n", encoding="utf-8")
    setter({"user": key}, tasks=[], variables={"token": "abc"},
           csv_sources=[{"name": "users", "file_path": str(csv_file)}])
    assert parameter_resolver.resolve("${var.token}") == "abc"
    assert parameter_resolver.resolve("${csv.users.login}") == "alice"
    assert parameter_resolver.resolve("${csv.users.login}") == "bob"


@pytest.mark.parametrize("key, setter, user_cls, specific", SETTER_CASES, ids=SETTER_IDS)
def test_run_tasks_feeds_dict_entries_from_both_task_shapes(monkeypatch, env, key, setter, user_cls, specific):
    proxy = fresh_proxy(monkeypatch, key)
    user = user_cls(env)
    seen: List[Dict[str, Any]] = []
    monkeypatch.setattr(user, "_do_step", seen.append)

    user.run_tasks()
    assert seen == []

    proxy.tasks = [{"method": "a"}, "not-a-dict", {"method": "b"}]
    user.run_tasks()
    assert seen == [{"method": "a"}, {"method": "b"}]

    seen.clear()
    proxy.tasks = {"tasks": [{"method": "c"}]}
    user.run_tasks()
    assert seen == [{"method": "c"}]


# ---------------------------------------------------------------------------
# AMQP (pika)
# ---------------------------------------------------------------------------


class FakeAmqpChannel:
    def __init__(self, messages: List[bytes]) -> None:
        self.declared: List[Dict[str, Any]] = []
        self.published: List[Dict[str, Any]] = []
        self.messages = list(messages)
        self.gets = 0

    def queue_declare(self, **kwargs: Any) -> None:
        self.declared.append(kwargs)

    def basic_publish(self, **kwargs: Any) -> None:
        self.published.append(kwargs)

    def basic_get(self, queue: str, auto_ack: bool):
        self.gets += 1
        if not self.messages:
            return None, None, None
        return SimpleNamespace(queue=queue, auto_ack=auto_ack), None, self.messages.pop(0)


def install_fake_pika(monkeypatch, messages: Optional[List[bytes]] = None) -> SimpleNamespace:
    record = SimpleNamespace(params=None, channel=FakeAmqpChannel(messages or []), closed=0)

    class FakeBlockingConnection:
        def __init__(self, params: Any) -> None:
            record.params = params

        def channel(self) -> FakeAmqpChannel:
            return record.channel

        def close(self) -> None:
            record.closed += 1

    fake = make_module("pika", URLParameters=lambda url: ("url-params", url),
                       BlockingConnection=FakeBlockingConnection)
    monkeypatch.setitem(sys.modules, "pika", fake)
    return record


def test_amqp_connect_opens_channel_from_url(monkeypatch, env):
    record = install_fake_pika(monkeypatch)
    user = amqp_t.AmqpUserWrapper(env)
    user._do_step({"method": "CONNECT", "url": "amqp://u:p@mq:5672/%2F"})
    assert_success(env, "AMQP", "connect", 0)
    assert record.params == ("url-params", "amqp://u:p@mq:5672/%2F")
    assert user._channel is record.channel


def test_amqp_declare_publish_consume_close(monkeypatch, env):
    record = install_fake_pika(monkeypatch, messages=[b"ab", b"cde"])
    user = amqp_t.AmqpUserWrapper(env)
    user._do_step({"method": "connect"})
    assert record.params == ("url-params", amqp_t.AmqpUserWrapper.host)

    user._do_step({"method": "declare_queue", "queue": "q", "durable": 1})
    assert record.channel.declared == [
        {"queue": "q", "durable": True, "exclusive": False, "auto_delete": False}]

    user._do_step({"method": "publish", "routing_key": "q", "body": "hé", "name": "pub"})
    assert record.channel.published == [{"exchange": "", "routing_key": "q", "body": "hé".encode("utf-8")}]

    user._do_step({"method": "consume", "queue": "q", "max_messages": 5})
    assert record.channel.gets == 3

    user._do_step({"method": "close"})
    assert record.closed == 1
    assert user._connection is None and user._channel is None

    assert [e["name"] for e in env.fired] == ["connect", "declare_queue", "pub", "consume", "close"]
    assert [e["response_length"] for e in env.fired] == [0, 0, 3, 5, 0]
    assert all(e["exception"] is None and e["request_type"] == "AMQP" for e in env.fired)


@pytest.mark.parametrize("method", ["declare_queue", "publish", "consume"])
def test_amqp_channel_operations_fail_before_connect(env, method):
    amqp_t.AmqpUserWrapper(env)._do_step({"method": method, "queue": "q"})
    assert_failure(env, "AMQP", method, RuntimeError, "channel not open")


def test_amqp_close_clears_state_even_when_close_raises(env):
    user = amqp_t.AmqpUserWrapper(env)

    def broken_close() -> None:
        raise OSError("socket gone")

    user._connection = SimpleNamespace(close=broken_close)
    user._channel = object()
    user._do_step({"method": "close"})
    assert_failure(env, "AMQP", "close", OSError, "socket gone")
    assert user._connection is None and user._channel is None


def test_amqp_unknown_method_fires_nothing(env):
    amqp_t.AmqpUserWrapper(env)._do_step({"method": "purge"})
    assert env.fired == []


def test_amqp_missing_pika_reports_runtime_error(monkeypatch, env):
    block_import(monkeypatch, "pika")
    amqp_t.AmqpUserWrapper(env)._do_step({"method": "connect"})
    assert_failure(env, "AMQP", "connect", RuntimeError, "pip install pika")


# ---------------------------------------------------------------------------
# APNS (httpx HTTP/2)
# ---------------------------------------------------------------------------


class FakeHttpxClient:
    """Minimal ``httpx.Client`` replacement shared by the APNS and async HTTP tests."""

    def __init__(self, record: SimpleNamespace, **kwargs: Any) -> None:
        self.record = record
        record.client_kwargs.append(kwargs)

    def post(self, path: str, content: bytes, headers: Dict[str, str]) -> SimpleNamespace:
        self.record.calls.append({"path": path, "content": content, "headers": headers})
        return self._respond()

    def request(self, method: str, url: str, **kwargs: Any) -> SimpleNamespace:
        self.record.calls.append({"method": method, "url": url, "kwargs": kwargs})
        return self._respond()

    def _respond(self) -> SimpleNamespace:
        if self.record.error is not None:
            raise self.record.error
        return self.record.response

    def close(self) -> None:
        self.record.closed += 1


def install_fake_httpx(monkeypatch, response: Any = None, error: Optional[BaseException] = None) -> SimpleNamespace:
    record = SimpleNamespace(client_kwargs=[], calls=[], closed=0, response=response, error=error)
    fake = make_module("httpx", Client=lambda **kwargs: FakeHttpxClient(record, **kwargs))
    monkeypatch.setitem(sys.modules, "httpx", fake)
    return record


def test_apns_send_posts_payload_with_headers(monkeypatch, env):
    record = install_fake_httpx(monkeypatch, response=SimpleNamespace(status_code=200, content=b"ok!"))
    user = apns_t.ApnsUserWrapper(env)
    user._do_step({"method": "send", "device_token": "dev1", "topic": "com.x", "jwt": "J",
                   "payload": {"aps": {"alert": "hi"}}, "endpoint": "https://sandbox", "timeout": 3})
    assert_success(env, "APNS", "send", 3)
    assert record.client_kwargs == [{"http2": True, "base_url": "https://sandbox", "timeout": 3.0}]
    call = record.calls[0]
    assert call["path"] == "/3/device/dev1"
    assert json.loads(call["content"]) == {"aps": {"alert": "hi"}}
    assert call["headers"] == {"apns-topic": "com.x", "content-type": "application/json",
                               "authorization": "bearer J"}


def test_apns_reuses_client_and_omits_auth_without_jwt(monkeypatch, env):
    record = install_fake_httpx(monkeypatch, response=SimpleNamespace(status_code=200, content=b""))
    user = apns_t.ApnsUserWrapper(env)
    user._do_step({"method": "send", "device_token": "a"})
    user._do_step({"method": "send", "device_token": "b", "name": "second"})
    assert len(record.client_kwargs) == 1
    assert record.client_kwargs[0]["base_url"] == apns_t.ApnsUserWrapper.host
    assert "authorization" not in record.calls[0]["headers"]
    assert json.loads(record.calls[0]["content"]) == {}
    assert [e["name"] for e in env.fired] == ["send", "second"]


def test_apns_send_without_device_token_fails(monkeypatch, env):
    install_fake_httpx(monkeypatch, response=SimpleNamespace(status_code=200, content=b""))
    apns_t.ApnsUserWrapper(env)._do_step({"method": "send"})
    assert_failure(env, "APNS", "send", KeyError, "device_token")


def test_apns_transport_error_is_reported(monkeypatch, env):
    install_fake_httpx(monkeypatch, error=ConnectionError("refused"))
    apns_t.ApnsUserWrapper(env)._do_step({"method": "send", "device_token": "t"})
    assert_failure(env, "APNS", "send", ConnectionError, "refused")


def test_apns_close_releases_client(monkeypatch, env):
    record = install_fake_httpx(monkeypatch, response=SimpleNamespace(status_code=200, content=b""))
    user = apns_t.ApnsUserWrapper(env)
    user._do_step({"method": "send", "device_token": "t"})
    user._do_step({"method": "close"})
    assert record.closed == 1
    assert user._client is None
    assert env.fired[-1]["exception"] is None


def test_apns_unknown_method_and_missing_httpx(monkeypatch, env):
    user = apns_t.ApnsUserWrapper(env)
    user._do_step({"method": "subscribe"})
    assert env.fired == []
    block_import(monkeypatch, "httpx")
    user._do_step({"method": "send", "device_token": "t"})
    assert_failure(env, "APNS", "send", RuntimeError, "httpx is required")


# ---------------------------------------------------------------------------
# Async HTTP (httpx)
# ---------------------------------------------------------------------------


def http_response(status: int = 200, text: str = "hello world") -> SimpleNamespace:
    return SimpleNamespace(status_code=status, text=text, content=text.encode("utf-8"))


def test_async_http_request_forwards_filtered_kwargs(monkeypatch, env):
    fresh_proxy(monkeypatch, "async_http_user")
    record = install_fake_httpx(monkeypatch, response=http_response())
    user = async_http_t.AsyncHttpUserWrapper(env)
    user._do_step({"method": "post", "request_url": "http://svc/api", "json": {"a": 1},
                   "headers": {"h": "v"}, "params": None, "allow_redirects": 0, "verify": False})
    assert_success(env, "HTTPX", "http://svc/api", len(b"hello world"))
    assert record.client_kwargs == [{"http2": False, "timeout": 30.0}]
    assert record.calls == [{"method": "POST", "url": "http://svc/api",
                             "kwargs": {"json": {"a": 1}, "headers": {"h": "v"}, "follow_redirects": False}}]


def test_async_http_uses_http2_flag_from_proxy_and_url_alias(monkeypatch, env):
    proxy = fresh_proxy(monkeypatch, "async_http_user")
    proxy.configure({}, http2=True)
    record = install_fake_httpx(monkeypatch, response=http_response())
    async_http_t.AsyncHttpUserWrapper(env)._do_step({"method": "get", "url": "http://svc/", "name": "home"})
    assert record.client_kwargs[0]["http2"] is True
    assert_success(env, "HTTPX", "home")


def test_async_http_passing_assertions_report_success(monkeypatch, env):
    fresh_proxy(monkeypatch, "async_http_user")
    install_fake_httpx(monkeypatch, response=http_response(201, "created ok"))
    async_http_t.AsyncHttpUserWrapper(env)._do_step({
        "method": "put", "url": "http://svc/x",
        "assertions": [{"type": "status_code", "value": 201}, {"type": "contains", "value": "ok"}]})
    assert_success(env, "HTTPX", "http://svc/x")


@pytest.mark.parametrize("assertion, message", [
    ({"type": "status_code", "value": 200}, "status_code expected 200, got 500"),
    ({"type": "contains", "value": "absent"}, "body does not contain 'absent'"),
])
def test_async_http_failed_assertion_sets_exception(monkeypatch, env, assertion, message):
    fresh_proxy(monkeypatch, "async_http_user")
    install_fake_httpx(monkeypatch, response=http_response(500, "boom"))
    async_http_t.AsyncHttpUserWrapper(env)._do_step(
        {"method": "get", "url": "http://svc/x", "assertions": [assertion]})
    event = single_event(env, "HTTPX", "http://svc/x")
    assert isinstance(event["exception"], AssertionError)
    assert str(event["exception"]) == message
    assert event["response_length"] == len(b"boom")


def test_async_http_client_error_is_reported(monkeypatch, env):
    fresh_proxy(monkeypatch, "async_http_user")
    install_fake_httpx(monkeypatch, error=TimeoutError("slow"))
    async_http_t.AsyncHttpUserWrapper(env)._do_step({"method": "get", "url": "http://svc/x"})
    assert_failure(env, "HTTPX", "http://svc/x", TimeoutError, "slow")


@pytest.mark.parametrize("step", [{"method": "get"}, {"url": "http://svc/x"}, {"method": "", "url": "http://x"}])
def test_async_http_incomplete_step_fires_nothing(monkeypatch, env, step):
    record = install_fake_httpx(monkeypatch, response=http_response())
    async_http_t.AsyncHttpUserWrapper(env)._do_step(step)
    assert env.fired == []
    assert record.calls == []


def test_async_http_missing_httpx_reports_runtime_error(monkeypatch, env):
    block_import(monkeypatch, "httpx")
    async_http_t.AsyncHttpUserWrapper(env)._do_step({"method": "get", "url": "http://svc/x"})
    assert_failure(env, "HTTPX", "http://svc/x", RuntimeError, "httpx is required")


# ---------------------------------------------------------------------------
# Cassandra (cassandra-driver)
# ---------------------------------------------------------------------------


def install_fake_cassandra(monkeypatch, rows: Optional[List[Any]] = None) -> SimpleNamespace:
    record = SimpleNamespace(cluster_kwargs=None, keyspace="unset", executed=[], shutdowns=[])

    class FakeSession:
        def execute(self, cql: str, params: Any) -> List[Any]:
            record.executed.append((cql, params))
            return iter(rows or [])

        def shutdown(self) -> None:
            record.shutdowns.append("session")

    class FakeCluster:
        def __init__(self, **kwargs: Any) -> None:
            record.cluster_kwargs = kwargs

        def connect(self, keyspace: Optional[str]) -> FakeSession:
            record.keyspace = keyspace
            return FakeSession()

        def shutdown(self) -> None:
            record.shutdowns.append("cluster")

    monkeypatch.setitem(sys.modules, "cassandra", make_module("cassandra"))
    monkeypatch.setitem(sys.modules, "cassandra.cluster", make_module("cassandra.cluster", Cluster=FakeCluster))
    return record


def test_cassandra_connect_execute_shutdown(monkeypatch, env):
    record = install_fake_cassandra(monkeypatch, rows=[("a", 1), ("bb", 22)])
    user = cassandra_t.CassandraUserWrapper(env)
    user._do_step({"method": "connect", "contact_points": ["10.0.0.9"], "port": "9043", "keyspace": "demo"})
    user._do_step({"method": "execute", "cql": "SELECT * FROM t WHERE id=%s", "parameters": [7], "name": "q"})
    user._do_step({"method": "shutdown"})
    assert record.cluster_kwargs == {"contact_points": ["10.0.0.9"], "port": 9043}
    assert record.keyspace == "demo"
    assert record.executed == [("SELECT * FROM t WHERE id=%s", [7])]
    assert record.shutdowns == ["session", "cluster"]
    assert user._session is None and user._cluster is None
    assert [e["name"] for e in env.fired] == ["connect", "q", "shutdown"]
    assert [e["response_length"] for e in env.fired] == [0, len("('a', 1)") + len("('bb', 22)"), 0]
    assert all(e["exception"] is None and e["request_type"] == "CASSANDRA" for e in env.fired)


def test_cassandra_defaults_and_empty_parameters(monkeypatch, env):
    record = install_fake_cassandra(monkeypatch)
    user = cassandra_t.CassandraUserWrapper(env)
    user._do_step({"method": "connect"})
    user._do_step({"method": "execute", "cql": "SELECT 1", "parameters": []})
    assert record.cluster_kwargs == {"contact_points": [cassandra_t.CassandraUserWrapper.host], "port": 9042}
    assert record.keyspace is None
    assert record.executed == [("SELECT 1", None)]
    assert env.fired[-1]["response_length"] == 0


def test_cassandra_execute_before_connect_fails(env):
    cassandra_t.CassandraUserWrapper(env)._do_step({"method": "execute", "cql": "SELECT 1"})
    assert_failure(env, "CASSANDRA", "execute", RuntimeError, "session not open")


def test_cassandra_unknown_method_and_missing_driver(monkeypatch, env):
    user = cassandra_t.CassandraUserWrapper(env)
    user._do_step({"method": "truncate"})
    assert env.fired == []
    block_import(monkeypatch, "cassandra", "cassandra.cluster")
    user._do_step({"method": "connect"})
    assert_failure(env, "CASSANDRA", "connect", RuntimeError, "pip install cassandra-driver")


# ---------------------------------------------------------------------------
# CoAP (aiocoap)
# ---------------------------------------------------------------------------


def install_fake_aiocoap(monkeypatch, payload: bytes = b"23.5",
                         error: Optional[BaseException] = None) -> SimpleNamespace:
    record = SimpleNamespace(messages=[], shutdowns=0)

    class FakeContext:
        @classmethod
        async def create_client_context(cls) -> "FakeContext":
            return cls()

        def request(self, message: Any) -> SimpleNamespace:
            record.messages.append(message)

            async def respond() -> SimpleNamespace:
                if error is not None:
                    raise error
                return SimpleNamespace(code="2.05 Content", payload=payload)

            return SimpleNamespace(response=respond())

        async def shutdown(self) -> None:
            record.shutdowns += 1

    code = SimpleNamespace(GET="GET", POST="POST", PUT="PUT", DELETE="DELETE")
    fake = make_module("aiocoap", Context=FakeContext, Message=lambda **kwargs: kwargs,
                       numbers=SimpleNamespace(codes=SimpleNamespace(Code=code)))
    monkeypatch.setitem(sys.modules, "aiocoap", fake)
    return record


def test_coap_get_sends_message_and_reports_payload_length(monkeypatch, env):
    record = install_fake_aiocoap(monkeypatch, payload=b"12345")
    coap_t.CoapUserWrapper(env)._do_step({"method": "GET", "uri": "coap://dev/.well-known/core"})
    assert_success(env, "COAP", "coap://dev/.well-known/core", 5)
    assert record.messages == [{"code": "GET", "uri": "coap://dev/.well-known/core", "payload": b""}]
    assert record.shutdowns == 1


@pytest.mark.parametrize("method, code", [("post", "POST"), ("put", "PUT"), ("delete", "DELETE")])
def test_coap_methods_map_to_codes_and_encode_payload(monkeypatch, env, method, code):
    record = install_fake_aiocoap(monkeypatch)
    coap_t.CoapUserWrapper(env)._do_step({"method": method, "uri": "coap://dev/s", "payload": "on", "name": "s"})
    assert_success(env, "COAP", "s", len(b"23.5"))
    assert record.messages[0]["code"] == code
    assert record.messages[0]["payload"] == b"on"


def test_coap_request_error_still_shuts_context_down(monkeypatch, env):
    record = install_fake_aiocoap(monkeypatch, error=TimeoutError("no ack"))
    coap_t.CoapUserWrapper(env)._do_step({"method": "get", "uri": "coap://dev/x"})
    assert_failure(env, "COAP", "coap://dev/x", TimeoutError, "no ack")
    assert record.shutdowns == 1


def test_coap_unknown_method_reports_value_error(monkeypatch, env):
    record = install_fake_aiocoap(monkeypatch)
    coap_t.CoapUserWrapper(env)._do_step({"method": "observe", "uri": "coap://dev/x"})
    assert_failure(env, "COAP", "coap://dev/x", ValueError, "unsupported coap method: observe")
    assert record.messages == []


def test_coap_missing_aiocoap_reports_runtime_error(monkeypatch, env):
    block_import(monkeypatch, "aiocoap")
    coap_t.CoapUserWrapper(env)._do_step({"method": "get", "uri": "coap://dev/x"})
    assert_failure(env, "COAP", "coap://dev/x", RuntimeError, "pip install aiocoap")


# ---------------------------------------------------------------------------
# Consul (stdlib urllib)
# ---------------------------------------------------------------------------


def test_consul_put_sends_value_to_kv_url(monkeypatch, env):
    calls = patch_urlopen(monkeypatch)
    consul_t.ConsulUserWrapper(env)._do_step(
        {"method": "put", "key": "cfg/a b", "value": "yés", "addr": "http://c:8500/", "timeout": 2})
    assert_success(env, "CONSUL", "put", len("yés".encode("utf-8")))
    request = calls[0]["request"]
    assert request.get_method() == "PUT"
    assert request.full_url == "http://c:8500/v1/kv/cfg/a%20b"
    assert request.data == "yés".encode("utf-8")
    assert calls[0]["timeout"] == 2.0


def test_consul_get_delete_services(monkeypatch, env):
    calls = patch_urlopen(monkeypatch, body=b'[{"Key":"k"}]')
    user = consul_t.ConsulUserWrapper(env)
    user._do_step({"method": "get", "key": "k"})
    user._do_step({"method": "delete", "key": "k"})
    user._do_step({"method": "services", "name": "svc"})
    assert [(c["request"].get_method(), c["request"].full_url) for c in calls] == [
        ("GET", "http://127.0.0.1:8500/v1/kv/k"),
        ("DELETE", "http://127.0.0.1:8500/v1/kv/k"),
        ("GET", "http://127.0.0.1:8500/v1/agent/services"),
    ]
    assert [c["timeout"] for c in calls] == [5.0, 5.0, 5.0]
    assert [e["name"] for e in env.fired] == ["get", "delete", "svc"]
    assert [e["response_length"] for e in env.fired] == [13, 0, 13]
    assert all(e["exception"] is None and e["request_type"] == "CONSUL" for e in env.fired)


def test_consul_resolves_placeholders_before_request(monkeypatch, env):
    calls = patch_urlopen(monkeypatch)
    parameter_resolver.register_variable("tenant", "acme")
    consul_t.ConsulUserWrapper(env)._do_step({"method": "get", "key": "${var.tenant}/flag"})
    assert calls[0]["request"].full_url == "http://127.0.0.1:8500/v1/kv/acme/flag"


def test_consul_http_error_and_missing_key(monkeypatch, env):
    patch_urlopen(monkeypatch, error=urllib.error.URLError("down"))
    user = consul_t.ConsulUserWrapper(env)
    user._do_step({"method": "get", "key": "k"})
    assert_failure(env, "CONSUL", "get", urllib.error.URLError, "down")
    env.fired.clear()
    user._do_step({"method": "delete"})
    assert_failure(env, "CONSUL", "delete", KeyError, "key")


def test_consul_unknown_method_fires_nothing(monkeypatch, env):
    calls = patch_urlopen(monkeypatch)
    consul_t.ConsulUserWrapper(env)._do_step({"method": "watch", "key": "k"})
    assert env.fired == []
    assert calls == []


# ---------------------------------------------------------------------------
# Couchbase
# ---------------------------------------------------------------------------


def install_fake_couchbase(monkeypatch) -> SimpleNamespace:
    record = SimpleNamespace(cluster_args=None, bucket=None, ops=[], closed=0, store={})

    class FakeCollection:
        def upsert(self, key: str, value: Any) -> None:
            record.ops.append(("upsert", key))
            record.store[key] = value

        def get(self, key: str) -> SimpleNamespace:
            record.ops.append(("get", key))
            return SimpleNamespace(content_as={dict: record.store[key]})

        def remove(self, key: str) -> None:
            record.ops.append(("remove", key))
            record.store.pop(key)

    class FakeCluster:
        def __init__(self, url: str, options: Any) -> None:
            record.cluster_args = (url, options)

        def bucket(self, name: str) -> SimpleNamespace:
            record.bucket = name
            return SimpleNamespace(default_collection=FakeCollection)

        def close(self) -> None:
            record.closed += 1

    modules = {
        "couchbase": make_module("couchbase"),
        "couchbase.auth": make_module("couchbase.auth", PasswordAuthenticator=lambda u, p: ("auth", u, p)),
        "couchbase.cluster": make_module("couchbase.cluster", Cluster=FakeCluster),
        "couchbase.options": make_module("couchbase.options", ClusterOptions=lambda authenticator: authenticator),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    return record


def test_couchbase_connect_upsert_get_remove_close(monkeypatch, env):
    record = install_fake_couchbase(monkeypatch)
    user = couchbase_t.CouchbaseUserWrapper(env)
    user._do_step({"method": "connect", "url": "couchbase://cb", "user": "admin",
                   "password": "pw", "bucket": "travel"})
    user._do_step({"method": "upsert", "key": "k", "value": {"x": 1}})
    user._do_step({"method": "get", "key": "k", "name": "read"})
    user._do_step({"method": "remove", "key": "k"})
    user._do_step({"method": "close"})
    assert record.cluster_args == ("couchbase://cb", ("auth", "admin", "pw"))
    assert record.bucket == "travel"
    assert record.ops == [("upsert", "k"), ("get", "k"), ("remove", "k")]
    assert record.closed == 1 and user._collection is None
    assert [e["name"] for e in env.fired] == ["connect", "upsert", "read", "remove", "close"]
    assert [e["response_length"] for e in env.fired] == [0, len("{'x': 1}"), len("{'x': 1}"), 0, 0]
    assert all(e["exception"] is None and e["request_type"] == "COUCHBASE" for e in env.fired)


def test_couchbase_connect_defaults(monkeypatch, env):
    record = install_fake_couchbase(monkeypatch)
    couchbase_t.CouchbaseUserWrapper(env)._do_step({"method": "connect"})
    assert record.cluster_args == ("couchbase://127.0.0.1", ("auth", "Administrator", ""))
    assert record.bucket == "default"


@pytest.mark.parametrize("method", ["upsert", "get", "remove"])
def test_couchbase_operations_fail_before_connect(env, method):
    couchbase_t.CouchbaseUserWrapper(env)._do_step({"method": method, "key": "k"})
    assert_failure(env, "COUCHBASE", method, RuntimeError, "couchbase not connected")


def test_couchbase_unknown_method_and_missing_sdk(monkeypatch, env):
    user = couchbase_t.CouchbaseUserWrapper(env)
    user._do_step({"method": "query"})
    assert env.fired == []
    block_import(monkeypatch, "couchbase", "couchbase.auth", "couchbase.cluster", "couchbase.options")
    user._do_step({"method": "connect"})
    assert_failure(env, "COUCHBASE", "connect", RuntimeError, "pip install couchbase")


# ---------------------------------------------------------------------------
# Elasticsearch
# ---------------------------------------------------------------------------


def install_fake_elasticsearch(monkeypatch) -> SimpleNamespace:
    record = SimpleNamespace(hosts=None, calls=[], closed=0)

    class FakeElasticsearch:
        def __init__(self, hosts: List[str]) -> None:
            record.hosts = hosts

        def index(self, index: str, document: Dict[str, Any]) -> Dict[str, Any]:
            record.calls.append(("index", index, document))
            return {"result": "created"}

        def search(self, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
            record.calls.append(("search", index, body))
            return {"took": 1, "hits": {"hits": [{"_id": "1"}]}}

        def get(self, index: str, id: str) -> Dict[str, Any]:  # noqa: A002 - mirrors the client signature
            record.calls.append(("get", index, id))
            return {"_id": id, "found": True}

        def close(self) -> None:
            record.closed += 1

    monkeypatch.setitem(sys.modules, "elasticsearch", make_module("elasticsearch", Elasticsearch=FakeElasticsearch))
    return record


def test_elasticsearch_index_search_get_close(monkeypatch, env):
    record = install_fake_elasticsearch(monkeypatch)
    user = es_t.ElasticsearchUserWrapper(env)
    user._do_step({"method": "connect", "hosts": ["http://es:9200"]})
    user._do_step({"method": "index", "index": "logs", "document": {"msg": "hi"}})
    user._do_step({"method": "search", "index": "logs", "name": "find"})
    user._do_step({"method": "get", "index": "logs", "id": 7})
    user._do_step({"method": "close"})
    assert record.hosts == ["http://es:9200"]
    assert record.calls == [
        ("index", "logs", {"msg": "hi"}),
        ("search", "logs", {"query": {"match_all": {}}}),
        ("get", "logs", "7"),
    ]
    assert record.closed == 1 and user._client is None
    assert [e["name"] for e in env.fired] == ["connect", "index", "find", "get", "close"]
    assert [e["response_length"] for e in env.fired] == [
        0,
        len(json.dumps({"result": "created"})),
        len(json.dumps([{"_id": "1"}])),
        len(json.dumps({"_id": "7", "found": True})),
        0,
    ]
    assert all(e["exception"] is None and e["request_type"] == "ES" for e in env.fired)


def test_elasticsearch_connect_defaults_to_host(monkeypatch, env):
    record = install_fake_elasticsearch(monkeypatch)
    es_t.ElasticsearchUserWrapper(env)._do_step({"method": "connect"})
    assert record.hosts == [es_t.ElasticsearchUserWrapper.host]


@pytest.mark.parametrize("method", ["index", "search", "get"])
def test_elasticsearch_operations_fail_before_connect(env, method):
    es_t.ElasticsearchUserWrapper(env)._do_step({"method": method, "index": "i", "id": 1})
    assert_failure(env, "ES", method, RuntimeError, "not connected")


def test_elasticsearch_unknown_method_and_missing_client(monkeypatch, env):
    user = es_t.ElasticsearchUserWrapper(env)
    user._do_step({"method": "bulk"})
    assert env.fired == []
    block_import(monkeypatch, "elasticsearch")
    user._do_step({"method": "connect"})
    assert_failure(env, "ES", "connect", RuntimeError, "pip install elasticsearch")


# ---------------------------------------------------------------------------
# etcd (etcd3)
# ---------------------------------------------------------------------------


def install_fake_etcd3(monkeypatch, stored: Optional[bytes] = b"value") -> SimpleNamespace:
    record = SimpleNamespace(client_kwargs=None, calls=[], closed=0)

    class FakeEtcdClient:
        def put(self, key: str, value: Any) -> None:
            record.calls.append(("put", key, value))

        def get(self, key: str):
            record.calls.append(("get", key))
            return stored, None

        def delete(self, key: str) -> None:
            record.calls.append(("delete", key))

        def close(self) -> None:
            record.closed += 1

    def client(**kwargs: Any) -> FakeEtcdClient:
        record.client_kwargs = kwargs
        return FakeEtcdClient()

    monkeypatch.setitem(sys.modules, "etcd3", make_module("etcd3", client=client))
    return record


def test_etcd_connect_put_get_delete_close(monkeypatch, env):
    record = install_fake_etcd3(monkeypatch)
    user = etcd_t.EtcdUserWrapper(env)
    user._do_step({"method": "connect", "host": "etcd", "port": "2380"})
    user._do_step({"method": "put", "key": "k", "value": 42})
    user._do_step({"method": "get", "key": "k", "name": "read"})
    user._do_step({"method": "delete", "key": "k"})
    user._do_step({"method": "close"})
    assert record.client_kwargs == {"host": "etcd", "port": 2380}
    assert record.calls == [("put", "k", "42"), ("get", "k"), ("delete", "k")]
    assert record.closed == 1 and user._client is None
    assert [e["name"] for e in env.fired] == ["connect", "put", "read", "delete", "close"]
    assert [e["response_length"] for e in env.fired] == [0, 2, 5, 0, 0]
    assert all(e["exception"] is None and e["request_type"] == "ETCD" for e in env.fired)


def test_etcd_get_missing_key_has_zero_length(monkeypatch, env):
    install_fake_etcd3(monkeypatch, stored=None)
    user = etcd_t.EtcdUserWrapper(env)
    user._do_step({"method": "connect"})
    user._do_step({"method": "get", "key": "absent"})
    assert env.fired[-1]["exception"] is None
    assert env.fired[-1]["response_length"] == 0


@pytest.mark.parametrize("method", ["put", "get", "delete"])
def test_etcd_operations_fail_before_connect(env, method):
    etcd_t.EtcdUserWrapper(env)._do_step({"method": method, "key": "k"})
    assert_failure(env, "ETCD", method, RuntimeError, "etcd not connected")


def test_etcd_unknown_method_and_missing_client(monkeypatch, env):
    user = etcd_t.EtcdUserWrapper(env)
    user._do_step({"method": "watch"})
    assert env.fired == []
    block_import(monkeypatch, "etcd3")
    user._do_step({"method": "connect"})
    assert_failure(env, "ETCD", "connect", RuntimeError, "pip install etcd3")


# ---------------------------------------------------------------------------
# FCM (stdlib urllib)
# ---------------------------------------------------------------------------


def test_fcm_send_posts_message_with_bearer_token(monkeypatch, env):
    calls = patch_urlopen(monkeypatch, body=b'{"name":"m1"}')
    message = {"token": "device-x", "notification": {"title": "hi"}}
    fcm_t.FcmUserWrapper(env)._do_step({"method": "send", "project_id": "proj", "token": "ya29", "message": message})
    assert_success(env, "FCM", "send", len(b'{"name":"m1"}'))
    request = calls[0]["request"]
    assert request.get_method() == "POST"
    assert request.full_url == "https://fcm.googleapis.com/v1/projects/proj/messages:send"
    assert request.get_header("Authorization") == "Bearer ya29"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {"message": message}
    assert calls[0]["timeout"] == 10.0


def test_fcm_custom_endpoint_and_timeout(monkeypatch, env):
    calls = patch_urlopen(monkeypatch)
    fcm_t.FcmUserWrapper(env)._do_step({"method": "send", "project_id": "p", "token": "t",
                                        "endpoint": "http://emulator:9000/", "timeout": 1, "name": "push"})
    assert_success(env, "FCM", "push", 0)
    assert calls[0]["request"].full_url == "http://emulator:9000/v1/projects/p/messages:send"
    assert json.loads(calls[0]["request"].data) == {"message": {}}
    assert calls[0]["timeout"] == 1.0


def test_fcm_http_error_is_reported(monkeypatch, env):
    error = urllib.error.HTTPError("https://fcm", 401, "Unauthorized", {}, None)
    patch_urlopen(monkeypatch, error=error)
    fcm_t.FcmUserWrapper(env)._do_step({"method": "send", "project_id": "p", "token": "bad"})
    assert assert_failure(env, "FCM", "send", urllib.error.HTTPError) is error


def test_fcm_missing_token_and_unknown_method(monkeypatch, env):
    calls = patch_urlopen(monkeypatch)
    user = fcm_t.FcmUserWrapper(env)
    user._do_step({"method": "topic_subscribe"})
    assert env.fired == []
    user._do_step({"method": "send", "project_id": "p"})
    assert_failure(env, "FCM", "send", KeyError, "token")
    assert calls == []


# ---------------------------------------------------------------------------
# FTP (stdlib ftplib)
# ---------------------------------------------------------------------------


def install_fake_ftp(monkeypatch, listing: Optional[List[str]] = None, download: bytes = b"") -> SimpleNamespace:
    record = SimpleNamespace(timeout=None, connected=None, login=None, commands=[], stored=b"", quits=0)

    class FakeFTP:
        def __init__(self, timeout: float) -> None:
            record.timeout = timeout

        def connect(self, host: str, port: int) -> None:
            record.connected = (host, port)

        def login(self, user: str, password: str) -> None:
            record.login = (user, password)

        def retrlines(self, command: str, callback) -> None:
            record.commands.append(command)
            for line in listing or []:
                callback(line)

        def storbinary(self, command: str, handle) -> None:
            record.commands.append(command)
            record.stored = handle.read()

        def retrbinary(self, command: str, callback) -> None:
            record.commands.append(command)
            callback(download)

        def quit(self) -> None:
            record.quits += 1

    monkeypatch.setattr(ftp_t.ftplib, "FTP", FakeFTP)
    return record


def test_ftp_connect_login_list_quit(monkeypatch, env):
    record = install_fake_ftp(monkeypatch, listing=["-rw a.txt", "-rw bb.txt"])
    user = ftp_t.FtpUserWrapper(env)
    user._do_step({"method": "connect", "host": "ftp.local", "port": "2121", "timeout": 3})
    user._do_step({"method": "login", "username": "u", "password": "p"})
    user._do_step({"method": "list", "path": "/pub", "name": "ls"})
    user._do_step({"method": "quit"})
    assert record.timeout == 3.0
    assert record.connected == ("ftp.local", 2121)
    assert record.login == ("u", "p")
    assert record.commands == ["LIST /pub"]
    assert record.quits == 1 and user._client is None
    assert [e["name"] for e in env.fired] == ["connect", "login", "ls", "quit"]
    assert [e["response_length"] for e in env.fired] == [0, 0, len("-rw a.txt") + len("-rw bb.txt"), 0]
    assert all(e["exception"] is None and e["request_type"] == "FTP" for e in env.fired)


def test_ftp_connect_defaults(monkeypatch, env):
    record = install_fake_ftp(monkeypatch)
    ftp_t.FtpUserWrapper(env)._do_step({"method": "connect"})
    assert record.connected == ("127.0.0.1", 21)
    assert record.timeout == 10.0


def test_ftp_upload_and_download_transfer_files(monkeypatch, env, tmp_path):
    record = install_fake_ftp(monkeypatch, download=b"remote-bytes")
    source = tmp_path / "report.csv"
    source.write_bytes(b"a,b\n1,2\n")
    target = tmp_path / "out.bin"
    user = ftp_t.FtpUserWrapper(env)
    user._do_step({"method": "connect"})
    user._do_step({"method": "upload", "local": str(source)})
    user._do_step({"method": "download", "remote": "data.bin", "local": str(target)})
    assert record.commands == ["STOR report.csv", "RETR data.bin"]
    assert record.stored == b"a,b\n1,2\n"
    assert target.read_bytes() == b"remote-bytes"
    assert [e["response_length"] for e in env.fired] == [0, 8, len(b"remote-bytes")]
    assert all(e["exception"] is None for e in env.fired)


@pytest.mark.parametrize("method", ["login", "list", "upload", "download"])
def test_ftp_operations_fail_before_connect(env, method):
    ftp_t.FtpUserWrapper(env)._do_step({"method": method, "local": "x", "remote": "y"})
    assert_failure(env, "FTP", method, RuntimeError, "ftp client not connected")


def test_ftp_quit_without_connection_and_unknown_method(env):
    user = ftp_t.FtpUserWrapper(env)
    user._do_step({"method": "mkdir"})
    assert env.fired == []
    user._do_step({"method": "quit"})
    assert_success(env, "FTP", "quit", 0)


def test_ftp_quit_error_still_drops_client(env):
    user = ftp_t.FtpUserWrapper(env)

    def broken_quit() -> None:
        raise EOFError("closed by peer")

    user._client = SimpleNamespace(quit=broken_quit)
    user._do_step({"method": "quit"})
    assert_failure(env, "FTP", "quit", EOFError, "closed by peer")
    assert user._client is None


# ---------------------------------------------------------------------------
# Fuzz HTTP (stdlib urllib)
# ---------------------------------------------------------------------------


def test_fuzz_http_fires_one_event_per_variant(monkeypatch, env):
    calls = patch_urlopen(monkeypatch, body=b"pong")
    fuzz_t.FuzzHttpUserWrapper(env)._do_step(
        {"method": "post", "request_url": "http://svc/api?x=1", "fuzz_count": 3,
         "json": {"a": "b"}, "params": {"q": "v"}, "headers": {"X-N": 1}, "timeout": 2})
    assert len(env.fired) == 3
    assert all(e["request_type"] == "FUZZ" and e["name"] == "http://svc/api?x=1" for e in env.fired)
    assert all(e["exception"] is None and e["response_length"] == 4 for e in env.fired)
    assert all(e["response_time"] >= 0 for e in env.fired)
    for call in calls:
        request = call["request"]
        assert request.get_method() == "POST"
        assert request.full_url.startswith("http://svc/api?x=1&")
        assert request.get_header("Content-type") == "application/json"
        assert request.get_header("X-n") == "1"
        assert isinstance(json.loads(request.data), dict)
        assert call["timeout"] == 2.0


def test_fuzz_http_default_count_and_plain_get(monkeypatch, env):
    calls = patch_urlopen(monkeypatch)
    fuzz_t.FuzzHttpUserWrapper(env)._do_step({"request_url": "http://svc/", "name": "root"})
    assert len(env.fired) == 5
    assert {e["name"] for e in env.fired} == {"root"}
    assert all(c["request"].get_method() == "GET" and c["request"].data is None for c in calls)
    assert all(c["request"].full_url == "http://svc/" for c in calls)


def test_fuzz_http_errors_are_reported_per_variant(monkeypatch, env):
    patch_urlopen(monkeypatch, error=urllib.error.URLError("refused"))
    fuzz_t.FuzzHttpUserWrapper(env)._do_step({"request_url": "http://svc/", "fuzz_count": 2})
    assert len(env.fired) == 2
    assert all(isinstance(e["exception"], urllib.error.URLError) for e in env.fired)
    assert all(e["response_length"] == 0 for e in env.fired)


def test_fuzz_http_zero_count_sends_nothing(monkeypatch, env):
    calls = patch_urlopen(monkeypatch)
    fuzz_t.FuzzHttpUserWrapper(env)._do_step({"request_url": "http://svc/", "fuzz_count": 0})
    assert env.fired == []
    assert calls == []


# ---------------------------------------------------------------------------
# GraphQL over WebSocket (websocket-client)
# ---------------------------------------------------------------------------


class FakeWebSocket:
    def __init__(self, record: SimpleNamespace) -> None:
        self.record = record

    def send(self, data: str) -> None:
        self.record.sent.append(json.loads(data))

    def recv(self) -> str:
        return self.record.incoming.pop(0) if self.record.incoming else ""

    def settimeout(self, timeout: float) -> None:
        self.record.timeouts.append(timeout)

    def close(self) -> None:
        self.record.closed += 1


def install_fake_websocket(monkeypatch, incoming: List[str]) -> SimpleNamespace:
    record = SimpleNamespace(connect=None, sent=[], incoming=list(incoming), timeouts=[], closed=0)

    def create_connection(url: str, **kwargs: Any) -> FakeWebSocket:
        record.connect = {"url": url, **kwargs}
        return FakeWebSocket(record)

    monkeypatch.setitem(sys.modules, "websocket", make_module("websocket", create_connection=create_connection))
    return record


ACK = json.dumps({"type": "connection_ack"})


def test_graphql_ws_connect_sends_connection_init(monkeypatch, env):
    record = install_fake_websocket(monkeypatch, [ACK])
    user = gql_ws_t.GraphQLWebSocketUserWrapper(env)
    user._do_step({"method": "connect", "url": "wss://api/graphql", "headers": ["Auth: x"],
                   "init_payload": {"token": "t"}, "timeout": 2})
    assert_success(env, "GRAPHQL-WS", "connect", len(ACK))
    assert record.connect == {"url": "wss://api/graphql", "subprotocols": ["graphql-transport-ws"],
                              "timeout": 2.0, "header": ["Auth: x"]}
    assert record.sent == [{"type": "connection_init", "payload": {"token": "t"}}]


def test_graphql_ws_subscribe_stops_at_complete(monkeypatch, env):
    first = json.dumps({"id": "7", "type": "next", "payload": {"data": {"x": 1}}})
    done = json.dumps({"id": "7", "type": "complete"})
    record = install_fake_websocket(monkeypatch, [ACK, first, done, "unread"])
    user = gql_ws_t.GraphQLWebSocketUserWrapper(env)
    user._do_step({"method": "connect"})
    user._do_step({"method": "subscribe", "id": 7, "query": "subscription { x }", "variables": {"v": 1},
                   "operation_name": "X", "max_messages": 10, "timeout": 4, "name": "sub"})
    assert record.sent[1] == {"id": "7", "type": "subscribe",
                              "payload": {"query": "subscription { x }", "variables": {"v": 1}, "operationName": "X"}}
    assert record.timeouts == [4.0]
    assert record.incoming == ["unread"]
    event = env.fired[-1]
    assert event["name"] == "sub" and event["exception"] is None
    assert event["response_length"] == len(first) + len(done)


def test_graphql_ws_subscribe_respects_max_messages_and_non_json(monkeypatch, env):
    record = install_fake_websocket(monkeypatch, [ACK, "not-json", "{}", "extra"])
    user = gql_ws_t.GraphQLWebSocketUserWrapper(env)
    user._do_step({"method": "connect"})
    user._do_step({"method": "subscribe", "query": "subscription { y }", "max_messages": 2})
    assert record.incoming == ["extra"]
    assert env.fired[-1]["exception"] is None
    assert env.fired[-1]["response_length"] == len("not-json") + len("{}")


def test_graphql_ws_complete_and_close(monkeypatch, env):
    record = install_fake_websocket(monkeypatch, [ACK])
    user = gql_ws_t.GraphQLWebSocketUserWrapper(env)
    user._do_step({"method": "connect"})
    user._do_step({"method": "complete", "id": "3"})
    user._do_step({"method": "close"})
    assert record.sent[-1] == {"id": "3", "type": "complete"}
    assert env.fired[1]["response_length"] == len(json.dumps({"id": "3", "type": "complete"}))
    assert record.closed == 1 and user._ws is None
    assert all(e["exception"] is None and e["request_type"] == "GRAPHQL-WS" for e in env.fired)


def test_graphql_ws_without_connection(env):
    user = gql_ws_t.GraphQLWebSocketUserWrapper(env)
    user._do_step({"method": "complete"})
    user._do_step({"method": "close"})
    user._do_step({"method": "unsubscribe"})
    assert [(e["name"], e["response_length"], e["exception"]) for e in env.fired] == [
        ("complete", 0, None), ("close", 0, None)]
    env.fired.clear()
    user._do_step({"method": "subscribe", "query": "subscription { x }"})
    assert_failure(env, "GRAPHQL-WS", "subscribe", RuntimeError, "graphql-ws not connected")


def test_graphql_ws_subscribe_without_query_fails(monkeypatch, env):
    install_fake_websocket(monkeypatch, [ACK])
    user = gql_ws_t.GraphQLWebSocketUserWrapper(env)
    user._do_step({"method": "connect"})
    env.fired.clear()
    user._do_step({"method": "subscribe"})
    assert_failure(env, "GRAPHQL-WS", "subscribe", KeyError, "query")


def test_graphql_ws_missing_websocket_client(monkeypatch, env):
    block_import(monkeypatch, "websocket")
    gql_ws_t.GraphQLWebSocketUserWrapper(env)._do_step({"method": "connect"})
    assert_failure(env, "GRAPHQL-WS", "connect", RuntimeError, "pip install websocket-client")


# ---------------------------------------------------------------------------
# gRPC (grpcio)
# ---------------------------------------------------------------------------

STUB_MODULE = "fake_grpc_stubs_user_templates_a"
STUB_PATH = f"{STUB_MODULE}.GreeterStub"
REQUEST_PATH = f"{STUB_MODULE}.HelloRequest"


class FakeProto:
    def __init__(self, **fields: Any) -> None:
        self.fields = fields

    def ByteSize(self) -> int:  # NOSONAR mirrors the protobuf method name
        return 6


def install_fake_grpc(monkeypatch, error: Optional[BaseException] = None) -> SimpleNamespace:
    record = SimpleNamespace(channels=[], closed=[], calls=[])

    class FakeChannel:
        def __init__(self, target: str) -> None:
            self.target = target

        def close(self) -> None:
            record.closed.append(self.target)

    class GreeterStub:
        def __init__(self, channel: FakeChannel) -> None:
            self.channel = channel

        def SayHello(self, request: FakeProto, timeout: float, metadata: Any) -> FakeProto:  # NOSONAR
            record.calls.append({"target": self.channel.target, "request": request.fields,
                                 "timeout": timeout, "metadata": metadata})
            if error is not None:
                raise error
            return FakeProto()

        def ListGreetings(self, request: FakeProto, timeout: float, metadata: Any):  # NOSONAR
            return iter([FakeProto(), FakeProto(), FakeProto()])

    def insecure_channel(target: str) -> FakeChannel:
        channel = FakeChannel(target)
        record.channels.append(channel)
        return channel

    monkeypatch.setitem(sys.modules, "grpc", make_module("grpc", insecure_channel=insecure_channel))
    monkeypatch.setitem(sys.modules, STUB_MODULE,
                        make_module(STUB_MODULE, GreeterStub=GreeterStub, HelloRequest=FakeProto))
    return record


def grpc_step(**overrides: Any) -> Dict[str, Any]:
    step = {"stub_path": STUB_PATH, "request_path": REQUEST_PATH, "method": "SayHello"}
    step.update(overrides)
    return step


def test_grpc_unary_call_builds_request_and_reports_size(monkeypatch, env):
    record = install_fake_grpc(monkeypatch)
    grpc_t.GrpcUserWrapper(env)._do_step(grpc_step(target="svc:50051", payload={"name": "w"},
                                                   metadata={"x-token": 1}, timeout="2.5"))
    event = assert_success(env, "GRPC", f"{STUB_PATH}.SayHello", 6)
    assert event["url"] == "svc:50051"
    assert record.calls == [{"target": "svc:50051", "request": {"name": "w"}, "timeout": 2.5,
                             "metadata": (("x-token", "1"),)}]


def test_grpc_target_falls_back_to_host_and_channel_is_reused(monkeypatch, env):
    record = install_fake_grpc(monkeypatch)
    user = grpc_t.GrpcUserWrapper(env)
    user._do_step(grpc_step(name="a", metadata=[["k", "v"], ["bad"]]))
    user._do_step(grpc_step(name="b"))
    user._do_step(grpc_step(name="c", host="other:1"))
    assert [c.target for c in record.channels] == ["localhost:50051", "other:1"]
    assert record.closed == ["localhost:50051"]
    assert record.calls[0]["metadata"] == (("k", "v"),)
    assert record.calls[0]["timeout"] == 10.0
    assert [(e["name"], e["url"], e["exception"]) for e in env.fired] == [
        ("a", "localhost:50051", None), ("b", "localhost:50051", None), ("c", "other:1", None)]


def test_grpc_server_stream_sums_message_sizes(monkeypatch, env):
    install_fake_grpc(monkeypatch)
    grpc_t.GrpcUserWrapper(env)._do_step(grpc_step(method="ListGreetings", rpc="SERVER_STREAM", name="list"))
    assert_success(env, "GRPC", "list", 18)


def test_grpc_rpc_error_is_reported(monkeypatch, env):
    install_fake_grpc(monkeypatch, error=RuntimeError("UNAVAILABLE"))
    grpc_t.GrpcUserWrapper(env)._do_step(grpc_step(name="hello"))
    assert_failure(env, "GRPC", "hello", RuntimeError, "UNAVAILABLE")


def test_grpc_unknown_rpc_method_is_reported(monkeypatch, env):
    install_fake_grpc(monkeypatch)
    grpc_t.GrpcUserWrapper(env)._do_step(grpc_step(method="Missing"))
    assert_failure(env, "GRPC", f"{STUB_PATH}.Missing", AttributeError, "Missing")


@pytest.mark.parametrize("stub_path", ["../evil.Stub", "NoModule", "os.path;rm"])
def test_grpc_rejects_unsafe_stub_path(monkeypatch, env, stub_path):
    install_fake_grpc(monkeypatch)
    grpc_t.GrpcUserWrapper(env)._do_step(grpc_step(stub_path=stub_path, name="s"))
    assert_failure(env, "GRPC", "s", ImportError, "invalid dotted import path")


def test_grpc_missing_grpcio_reports_runtime_error(monkeypatch, env):
    block_import(monkeypatch, "grpc")
    grpc_t.GrpcUserWrapper(env)._do_step(grpc_step(name="s"))
    assert_failure(env, "GRPC", "s", RuntimeError, "grpcio is required")


@pytest.mark.parametrize("value, body", [
    (5, b"5"),
    (2.5, b"2.5"),
    ({"a": 1}, b'{"a": 1}'),
    (b"\x01raw", b"\x01raw"),
])
def test_consul_put_encodes_non_text_values(monkeypatch, env, value, body):
    calls = patch_urlopen(monkeypatch)
    consul_t.ConsulUserWrapper(env)._do_step({"method": "put", "key": "k", "value": value})
    assert_success(env, "CONSUL", "put", len(body))
    assert calls[0]["request"].data == body


@pytest.mark.parametrize("payload, body", [(3, b"3"), ({"on": True}, b'{"on": true}')])
def test_coap_encodes_non_text_payloads(monkeypatch, env, payload, body):
    record = install_fake_aiocoap(monkeypatch)
    coap_t.CoapUserWrapper(env)._do_step({"method": "put", "uri": "coap://d/s", "payload": payload})
    assert record.messages[0]["payload"] == body
