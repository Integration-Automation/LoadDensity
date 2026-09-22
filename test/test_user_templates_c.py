import json
import sys
import types
import urllib.error
import urllib.request
from types import SimpleNamespace

import pytest

from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.utils.reliability import network_conditioner
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template import scenario_runner
from je_load_density.wrapper.user_template import smtp_user_template as smtp_mod
from je_load_density.wrapper.user_template import socket_user_template as socket_mod
from je_load_density.wrapper.user_template.smtp_user_template import SmtpUserWrapper, set_wrapper_smtp_user
from je_load_density.wrapper.user_template.snmp_user_template import SnmpUserWrapper, set_wrapper_snmp_user
from je_load_density.wrapper.user_template.soap_user_template import SoapUserWrapper, set_wrapper_soap_user
from je_load_density.wrapper.user_template.socket_user_template import SocketUserWrapper, set_wrapper_socket_user
from je_load_density.wrapper.user_template.sql_user_template import SqlUserWrapper, set_wrapper_sql_user
from je_load_density.wrapper.user_template.sse_user_template import SseUserWrapper, set_wrapper_sse_user
from je_load_density.wrapper.user_template.thrift_user_template import ThriftUserWrapper, set_wrapper_thrift_user
from je_load_density.wrapper.user_template.vault_user_template import VaultUserWrapper, set_wrapper_vault_user
from je_load_density.wrapper.user_template.webpush_user_template import (
    WebPushUserWrapper,
    set_wrapper_webpush_user,
)
from je_load_density.wrapper.user_template.websocket_user_template import (
    WebSocketUserWrapper,
    set_wrapper_websocket_user,
)
from je_load_density.wrapper.user_template.zmq_user_template import ZmqUserWrapper, set_wrapper_zmq_user


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class FakeRequestEvent:
    """Stands in for ``environment.events.request`` and records every fire."""

    def __init__(self):
        self.calls = []

    def fire(self, **kwargs):
        self.calls.append(kwargs)


class FakeEnvironment:
    def __init__(self):
        self.events = SimpleNamespace(request=FakeRequestEvent())


def make_user(cls):
    env = FakeEnvironment()
    return cls(env), env.events.request.calls


def only_event(calls, request_type, name):
    assert len(calls) == 1, calls
    event = calls[0]
    assert event["request_type"] == request_type
    assert event["name"] == name
    assert event["response_time"] >= 0
    return event


def assert_ok(calls, request_type, name, length=None):
    event = only_event(calls, request_type, name)
    assert event["exception"] is None
    if length is not None:
        assert event["response_length"] == length
    return event


def assert_failed(calls, request_type, name, exc_type, fragment=""):
    event = only_event(calls, request_type, name)
    assert isinstance(event["exception"], exc_type), event["exception"]
    assert fragment in str(event["exception"])
    assert event["response_length"] == 0
    return event


def fake_module(monkeypatch, name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def hide_module(monkeypatch, *names):
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)


def fresh_proxy(monkeypatch, key):
    proxy = type(locust_wrapper_proxy.user_dict[key])()
    monkeypatch.setitem(locust_wrapper_proxy.user_dict, key, proxy)
    return proxy


class FakeHttpResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def install_urlopen(monkeypatch, payload=b"", error=None):
    seen = []

    def urlopen(request, timeout=None):
        seen.append({"request": request, "timeout": timeout})
        if error is not None:
            raise error
        return FakeHttpResponse(payload)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return seen


@pytest.fixture(autouse=True)
def isolated_resolver(monkeypatch):
    monkeypatch.setattr(parameter_resolver, "_variables", {})
    monkeypatch.setattr(parameter_resolver, "_csv_sources", {})


# ---------------------------------------------------------------------------
# set_wrapper_* and run_tasks (shared across every template in this group)
# ---------------------------------------------------------------------------

TEMPLATES = [
    (set_wrapper_smtp_user, "smtp_user", SmtpUserWrapper),
    (set_wrapper_snmp_user, "snmp_user", SnmpUserWrapper),
    (set_wrapper_soap_user, "soap_user", SoapUserWrapper),
    (set_wrapper_socket_user, "socket_user", SocketUserWrapper),
    (set_wrapper_sql_user, "sql_user", SqlUserWrapper),
    (set_wrapper_sse_user, "sse_user", SseUserWrapper),
    (set_wrapper_thrift_user, "thrift_user", ThriftUserWrapper),
    (set_wrapper_vault_user, "vault_user", VaultUserWrapper),
    (set_wrapper_webpush_user, "webpush_user", WebPushUserWrapper),
    (set_wrapper_websocket_user, "websocket_user", WebSocketUserWrapper),
    (set_wrapper_zmq_user, "zmq_user", ZmqUserWrapper),
]
TEMPLATE_IDS = [key for _, key, _ in TEMPLATES]


@pytest.mark.parametrize("setter, key, cls", TEMPLATES, ids=TEMPLATE_IDS)
def test_setter_configures_proxy_and_registers_sources(monkeypatch, tmp_path, setter, key, cls):
    proxy = fresh_proxy(monkeypatch, key)
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("login\nalice\nbob\n", encoding="utf-8")
    tasks = [{"method": "noop"}]

    result = setter(
        {"user": key},
        tasks=tasks,
        variables={"region": "eu"},
        csv_sources=[{"name": "users", "file_path": str(csv_file)}],
        marker="kept",
    )

    assert result is cls
    assert proxy.user_detail_dict == {"user": key}
    assert proxy.tasks == tasks
    assert proxy.extra == {"marker": "kept"}
    assert parameter_resolver.resolve("${var.region}") == "eu"
    assert parameter_resolver.resolve("${csv.users.login}") == "alice"
    assert parameter_resolver.resolve("${csv.users.login}") == "bob"


@pytest.mark.parametrize("setter, key, cls", TEMPLATES, ids=TEMPLATE_IDS)
def test_setter_ignores_malformed_variables_and_csv(monkeypatch, setter, key, cls):
    proxy = fresh_proxy(monkeypatch, key)
    assert setter({"user": key}, tasks=[], variables=["not", "a", "dict"], csv_sources={"x": 1}) is cls
    assert parameter_resolver._variables == {}
    assert parameter_resolver._csv_sources == {}
    assert proxy.tasks == []


@pytest.mark.parametrize("setter, key, cls", TEMPLATES, ids=TEMPLATE_IDS)
def test_run_tasks_feeds_dict_steps_in_order(monkeypatch, setter, key, cls):
    proxy = fresh_proxy(monkeypatch, key)
    proxy.tasks = {"tasks": [{"method": "a"}, "skip-me", {"method": "b"}]}
    user, _ = make_user(cls)
    seen = []
    monkeypatch.setattr(user, "_do_step", seen.append)
    user.run_tasks()
    assert seen == [{"method": "a"}, {"method": "b"}]


@pytest.mark.parametrize("tasks", [None, [], "not-a-list", {"tasks": None}])
@pytest.mark.parametrize("setter, key, cls", TEMPLATES, ids=TEMPLATE_IDS)
def test_run_tasks_skips_empty_or_invalid_payload(monkeypatch, setter, key, cls, tasks):
    proxy = fresh_proxy(monkeypatch, key)
    proxy.tasks = tasks
    user, calls = make_user(cls)
    seen = []
    monkeypatch.setattr(user, "_do_step", seen.append)
    user.run_tasks()
    assert seen == []
    assert calls == []


@pytest.mark.parametrize("cls", [
    SmtpUserWrapper, SnmpUserWrapper, SoapUserWrapper, ThriftUserWrapper,
    VaultUserWrapper, WebPushUserWrapper, ZmqUserWrapper,
])
def test_unknown_method_fires_nothing(cls):
    user, calls = make_user(cls)
    user._do_step({"method": "explode", "name": "x"})
    assert calls == []


def test_step_placeholders_resolve_before_dispatch(monkeypatch):
    parameter_resolver.register_variable("topic", "news")
    user, calls = make_user(ZmqUserWrapper)
    sock = FakeZmqSocket()
    user._socket = sock
    install_fake_zmq(monkeypatch)
    user._do_step({"method": "subscribe", "topic": "${var.topic}", "name": "sub-${var.topic}"})
    assert_ok(calls, "ZMQ", "sub-news", 0)
    assert sock.options == [("SUBSCRIBE", b"news")]


# ---------------------------------------------------------------------------
# SMTP
# ---------------------------------------------------------------------------

class FakeSmtp:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.args = (host, port, timeout)
        self.started_tls = False
        self.sent = []
        self.quit_called = False
        FakeSmtp.instances.append(self)

    def starttls(self):
        self.started_tls = True

    def noop(self):
        return (250, b"OK")

    def login(self, username, password):
        if password != "good":
            raise PermissionError("535 auth failed")
        return (235, b"Accepted")

    def send_message(self, message):
        self.sent.append(message)

    def quit(self):
        self.quit_called = True
        return (221, b"Bye")


class FakeSmtpSsl(FakeSmtp):
    pass


@pytest.fixture
def smtp_lib(monkeypatch):
    FakeSmtp.instances = []
    monkeypatch.setattr(smtp_mod, "smtplib", SimpleNamespace(SMTP=FakeSmtp, SMTP_SSL=FakeSmtpSsl))
    return FakeSmtp


def test_smtp_connect_plain_with_starttls(smtp_lib):
    user, calls = make_user(SmtpUserWrapper)
    user._do_step({"method": "CONNECT", "host": "mail", "port": "587", "timeout": "3", "tls": True})
    assert_ok(calls, "SMTP", "connect", 2)
    client = smtp_lib.instances[0]
    assert type(client) is FakeSmtp
    assert client.args == ("mail", 587, 3.0)
    assert client.started_tls is True


def test_smtp_connect_ssl_uses_smtp_ssl(smtp_lib):
    user, calls = make_user(SmtpUserWrapper)
    user._do_step({"method": "connect", "ssl": True, "name": "ssl-connect"})
    assert_ok(calls, "SMTP", "ssl-connect")
    client = smtp_lib.instances[0]
    assert type(client) is FakeSmtpSsl
    assert client.args == ("127.0.0.1", 25, 10.0)
    assert client.started_tls is False


@pytest.mark.parametrize("method", ["login", "send"])
def test_smtp_requires_connection(smtp_lib, method):
    user, calls = make_user(SmtpUserWrapper)
    user._do_step({"method": method})
    assert_failed(calls, "SMTP", method, RuntimeError, "not connected")


def test_smtp_login_success_and_client_error(smtp_lib):
    user, calls = make_user(SmtpUserWrapper)
    user._client = FakeSmtp("h", 25)
    user._do_step({"method": "login", "username": "u", "password": "good"})
    assert_ok(calls, "SMTP", "login", 2)
    calls.clear()
    user._do_step({"method": "login", "username": "u", "password": "bad"})
    assert_failed(calls, "SMTP", "login", PermissionError, "535")


def test_smtp_send_builds_message_and_reports_size(smtp_lib):
    user, calls = make_user(SmtpUserWrapper)
    client = FakeSmtp("h", 25)
    user._client = client
    user._do_step({
        "method": "send", "from": "a@x", "to": ["b@y", "c@z"],
        "subject": "hi", "body": "hello", "name": "mail",
    })
    message = client.sent[0]
    assert message["From"] == "a@x"
    assert message["To"] == "b@y, c@z"
    assert message["Subject"] == "hi"
    assert message.get_content().strip() == "hello"
    assert_ok(calls, "SMTP", "mail", length=len(message.as_bytes()))


def test_smtp_quit_closes_client_and_is_safe_without_one(smtp_lib):
    user, calls = make_user(SmtpUserWrapper)
    client = FakeSmtp("h", 25)
    user._client = client
    user._do_step({"method": "quit"})
    assert client.quit_called is True
    assert user._client is None
    assert_ok(calls, "SMTP", "quit", 2)
    calls.clear()
    user._do_step({"method": "quit"})
    assert_ok(calls, "SMTP", "quit", 0)


# ---------------------------------------------------------------------------
# SNMP
# ---------------------------------------------------------------------------

class FakeSnmpStatus:
    def __init__(self, text):
        self.text = text

    def __bool__(self):
        return True

    def prettyPrint(self):
        return self.text


def install_fake_pysnmp(monkeypatch, get_rows=None, walk_rows=None):
    recorded = {}

    def make_ctor(label):
        def ctor(*args, **kwargs):
            recorded.setdefault(label, []).append((args, kwargs))
            return (label, args)
        return ctor

    def get_cmd(*args):
        recorded["getCmd"] = args
        return iter(get_rows or [])

    def next_cmd(*args, **kwargs):
        recorded["nextCmd"] = (args, kwargs)
        return iter(walk_rows or [])

    hlapi = fake_module(
        monkeypatch, "pysnmp.hlapi",
        SnmpEngine=make_ctor("SnmpEngine"), CommunityData=make_ctor("CommunityData"),
        UdpTransportTarget=make_ctor("UdpTransportTarget"), ContextData=make_ctor("ContextData"),
        ObjectType=make_ctor("ObjectType"), ObjectIdentity=make_ctor("ObjectIdentity"),
        getCmd=get_cmd, nextCmd=next_cmd,
    )
    fake_module(monkeypatch, "pysnmp", hlapi=hlapi)
    return recorded


def test_snmp_get_builds_request_and_counts_varbinds(monkeypatch):
    recorded = install_fake_pysnmp(monkeypatch, get_rows=[(None, 0, 0, ["sysDescr=Linux", "x=1"])])
    user, calls = make_user(SnmpUserWrapper)
    user._do_step({"method": "get", "host": "10.0.0.1", "port": "1161", "community": "priv", "oid": "1.3.6"})
    assert_ok(calls, "SNMP", "1.3.6", len("sysDescr=Linux") + len("x=1"))
    assert recorded["CommunityData"] == [(("priv",), {"mpModel": 0})]
    assert recorded["UdpTransportTarget"] == [((("10.0.0.1", 1161),), {})]
    assert recorded["ObjectIdentity"] == [(("1.3.6",), {})]
    assert len(recorded["getCmd"]) == 5


@pytest.mark.parametrize("row, fragment", [
    (("requestTimedOut", 0, 0, []), "requestTimedOut"),
    ((None, FakeSnmpStatus("noSuchName"), 1, []), "noSuchName"),
])
def test_snmp_get_error_indication_and_status_fail(monkeypatch, row, fragment):
    install_fake_pysnmp(monkeypatch, get_rows=[row])
    user, calls = make_user(SnmpUserWrapper)
    user._do_step({"method": "get", "host": "h", "oid": "1.3", "name": "probe"})
    assert_failed(calls, "SNMP", "probe", RuntimeError, fragment)


def test_snmp_walk_sums_rows_until_error(monkeypatch):
    rows = [
        (None, 0, 0, ["aa"]),
        (None, 0, 0, ["bbb", "c"]),
        ("endOfMib", 0, 0, ["ignored"]),
        (None, 0, 0, ["never"]),
    ]
    recorded = install_fake_pysnmp(monkeypatch, walk_rows=rows)
    user, calls = make_user(SnmpUserWrapper)
    user._do_step({"method": "walk", "host": "h", "oid": "1.3.6.1"})
    assert_ok(calls, "SNMP", "1.3.6.1", 6)
    assert recorded["nextCmd"][1] == {"lexicographicMode": False}
    assert recorded["UdpTransportTarget"] == [((("h", 161),), {})]
    assert recorded["CommunityData"] == [(("public",), {"mpModel": 0})]


def test_snmp_missing_oid_fails(monkeypatch):
    install_fake_pysnmp(monkeypatch)
    user, calls = make_user(SnmpUserWrapper)
    user._do_step({"method": "get", "host": "h"})
    assert_failed(calls, "SNMP", "get", KeyError, "oid")


def test_snmp_missing_library_reports_runtime_error(monkeypatch):
    hide_module(monkeypatch, "pysnmp", "pysnmp.hlapi")
    user, calls = make_user(SnmpUserWrapper)
    user._do_step({"method": "get", "host": "h", "oid": "1.3"})
    assert_failed(calls, "SNMP", "1.3", RuntimeError, "pysnmp is required")


# ---------------------------------------------------------------------------
# SOAP
# ---------------------------------------------------------------------------

def test_soap_call_posts_envelope_with_headers(monkeypatch):
    seen = install_urlopen(monkeypatch, payload=b"<Resp>ok</Resp>")
    user, calls = make_user(SoapUserWrapper)
    user._do_step({
        "endpoint": "https://svc/soap", "action": "urn:Do", "envelope": "<env/>",
        "headers": {"X-Trace": 7}, "timeout": "2", "expect_contains": "ok",
    })
    assert_ok(calls, "SOAP", "urn:Do", len(b"<Resp>ok</Resp>"))
    request = seen[0]["request"]
    assert request.get_method() == "POST"
    assert request.full_url == "https://svc/soap"
    assert request.data == b"<env/>"
    assert request.get_header("Soapaction") == "urn:Do"
    assert request.get_header("Content-type") == "text/xml; charset=utf-8"
    assert request.get_header("X-trace") == "7"
    assert seen[0]["timeout"] == 2.0


def test_soap_expect_contains_mismatch_fails(monkeypatch):
    install_urlopen(monkeypatch, payload=b"<Fault/>")
    user, calls = make_user(SoapUserWrapper)
    user._do_step({"method": "call", "endpoint": "https://svc", "expect_contains": "Result", "name": "op"})
    assert_failed(calls, "SOAP", "op", AssertionError, "Result")


def test_soap_transport_error_is_reported(monkeypatch):
    install_urlopen(monkeypatch, error=urllib.error.URLError("refused"))
    user, calls = make_user(SoapUserWrapper)
    user._do_step({"method": "call", "endpoint": "https://svc"})
    assert_failed(calls, "SOAP", "call", urllib.error.URLError, "refused")


def test_soap_missing_endpoint_fails(monkeypatch):
    seen = install_urlopen(monkeypatch)
    user, calls = make_user(SoapUserWrapper)
    user._do_step({"method": "call", "envelope": "<e/>"})
    assert_failed(calls, "SOAP", "call", KeyError, "endpoint")
    assert seen == []


# ---------------------------------------------------------------------------
# Socket (TCP / UDP)
# ---------------------------------------------------------------------------

class FakeTcpConn:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = b""
        self.closed = False

    def sendall(self, data):
        self.sent += data

    def settimeout(self, value):
        self.timeout = value

    def recv(self, size):
        return self.chunks.pop(0)[:size] if self.chunks else b""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True
        return False


class FakeUdpSock:
    def __init__(self, reply=b""):
        self.reply = reply
        self.sent = []
        self.closed = False
        self.recv_sizes = []

    def settimeout(self, value):
        self.timeout = value

    def sendto(self, data, address):
        self.sent.append((data, address))

    def recvfrom(self, size):
        self.recv_sizes.append(size)
        return self.reply, ("peer", 1)

    def close(self):
        self.closed = True


def install_fake_socket(monkeypatch, tcp=None, udp=None, tcp_error=None):
    record = {}

    def create_connection(address, timeout=None):
        record["tcp"] = (address, timeout)
        if tcp_error is not None:
            raise tcp_error
        return tcp

    def make_socket(family, kind):
        record["udp"] = (family, kind)
        return udp

    fake = SimpleNamespace(create_connection=create_connection, socket=make_socket, AF_INET="inet", SOCK_DGRAM="dgram")
    monkeypatch.setattr(socket_mod, "socket", fake)
    return record


def test_socket_tcp_sends_hex_payload_and_reads_expected_bytes(monkeypatch):
    conn = FakeTcpConn([b"OK", b"!!", b"extra"])
    record = install_fake_socket(monkeypatch, tcp=conn)
    user, calls = make_user(SocketUserWrapper)
    user._do_step({
        "target": "127.0.0.1:9000", "payload": "hex:414243",
        "expect_bytes": 4, "expect_substring": "OK!", "timeout": 2,
    })
    event = assert_ok(calls, "TCP", "tcp:127.0.0.1:9000", 3 + 4)
    assert event["url"] == "127.0.0.1:9000"
    assert conn.sent == b"ABC"
    assert conn.closed is True
    assert record["tcp"] == (("127.0.0.1", 9000), 2.0)


def test_socket_tcp_stops_reading_on_eof(monkeypatch):
    install_fake_socket(monkeypatch, tcp=FakeTcpConn([b"hi"]))
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"target": "h:1", "payload": "ping", "expect_bytes": 10, "name": "short"})
    assert_ok(calls, "TCP", "short", 4 + 2)


def test_socket_tcp_substring_mismatch_fails(monkeypatch):
    install_fake_socket(monkeypatch, tcp=FakeTcpConn([b"NOPE"]))
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"target": "h:1", "payload": "x", "expect_bytes": 4, "expect_substring": "OK", "name": "t"})
    assert_failed(calls, "TCP", "t", AssertionError, "OK")


def test_socket_tcp_connection_error_is_reported(monkeypatch):
    install_fake_socket(monkeypatch, tcp_error=ConnectionRefusedError("refused"))
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"protocol": "TCP", "target": "h:1", "name": "t"})
    assert_failed(calls, "TCP", "t", ConnectionRefusedError, "refused")


def test_socket_udp_round_trip_closes_socket(monkeypatch):
    sock = FakeUdpSock(reply=b"pong")
    record = install_fake_socket(monkeypatch, udp=sock)
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"protocol": "udp", "target": "10.0.0.2:53", "payload": b"ping", "expect_bytes": 8,
                   "expect_substring": "po"})
    event = assert_ok(calls, "UDP", "udp:10.0.0.2:53", 8)
    assert event["url"] == "10.0.0.2:53"
    assert record["udp"] == ("inet", "dgram")
    assert sock.sent == [(b"ping", ("10.0.0.2", 53))]
    assert sock.recv_sizes == [8]
    assert sock.closed is True


def test_socket_udp_without_read_still_closes_on_failure(monkeypatch):
    sock = FakeUdpSock()
    install_fake_socket(monkeypatch, udp=sock)
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"protocol": "udp", "target": "h:5", "payload": "x", "expect_substring": "y", "name": "u"})
    assert_failed(calls, "UDP", "u", AssertionError)
    assert sock.recv_sizes == []
    assert sock.closed is True


def test_socket_unsupported_protocol_fires_failure(monkeypatch):
    record = install_fake_socket(monkeypatch)
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"protocol": "sctp", "target": "h:1"})
    assert_failed(calls, "SCTP", "sctp:h:1", ValueError, "unsupported protocol")
    assert record == {}


def test_socket_defaults_to_user_host(monkeypatch):
    conn = FakeTcpConn([])
    record = install_fake_socket(monkeypatch, tcp=conn)
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"payload": "x"})
    assert_ok(calls, "TCP", "tcp:127.0.0.1:9000", 1)
    assert record["tcp"] == (("127.0.0.1", 9000), 5.0)


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

class FakeSqlResult:
    def __init__(self, rows=None, rowcount=0):
        self.returns_rows = rows is not None
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchall(self):
        return list(self._rows)


class FakeSqlEngine:
    def __init__(self, url, result=None, error=None):
        self.url = url
        self.result = result
        self.error = error
        self.executed = []

    def connect(self):
        engine = self

        class _Conn:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def execute(self, statement, params):
                engine.executed.append((statement, params))
                if engine.error is not None:
                    raise engine.error
                return engine.result

        return _Conn()


def install_fake_sqlalchemy(monkeypatch, result=None, error=None):
    engines = []

    def create_engine(url, future=False):
        assert future is True
        engine = FakeSqlEngine(url, result, error)
        engines.append(engine)
        return engine

    fake_module(monkeypatch, "sqlalchemy", create_engine=create_engine, text=lambda sql: ("TEXT", sql))
    return engines


def test_sql_select_counts_rows_and_reuses_engine(monkeypatch):
    proxy = fresh_proxy(monkeypatch, "sql_user")
    proxy.connection_string = "postgresql://db/app"
    engines = install_fake_sqlalchemy(monkeypatch, result=FakeSqlResult(rows=[(1,), (2,)]))
    user, calls = make_user(SqlUserWrapper)
    user._do_step({"sql": "SELECT id FROM t WHERE a=:a", "params": {"a": 1}, "expect_rows": 2})
    user._do_step({"sql": "SELECT 1", "name": "second"})
    assert len(engines) == 1
    assert engines[0].url == "postgresql://db/app"
    assert engines[0].executed == [
        (("TEXT", "SELECT id FROM t WHERE a=:a"), {"a": 1}),
        (("TEXT", "SELECT 1"), {}),
    ]
    assert [c["name"] for c in calls] == ["sql", "second"]
    assert all(c["request_type"] == "SQL" and c["exception"] is None for c in calls)
    assert [c["response_length"] for c in calls] == [2, 2]


def test_sql_falls_back_to_user_host(monkeypatch):
    fresh_proxy(monkeypatch, "sql_user")
    engines = install_fake_sqlalchemy(monkeypatch, result=FakeSqlResult(rowcount=3))
    user, calls = make_user(SqlUserWrapper)
    user._do_step({"sql": "UPDATE t SET a=1", "name": "upd"})
    assert engines[0].url == "sqlite:///:memory:"
    assert_ok(calls, "SQL", "upd", 3)


def test_sql_expect_rows_mismatch_fails(monkeypatch):
    fresh_proxy(monkeypatch, "sql_user")
    install_fake_sqlalchemy(monkeypatch, result=FakeSqlResult(rows=[(1,)]))
    user, calls = make_user(SqlUserWrapper)
    user._do_step({"sql": "SELECT 1", "expect_rows": 5, "name": "q"})
    assert_failed(calls, "SQL", "q", AssertionError, "expected 5 rows, got 1")


def test_sql_driver_error_is_reported(monkeypatch):
    fresh_proxy(monkeypatch, "sql_user")
    install_fake_sqlalchemy(monkeypatch, error=LookupError("no such table"))
    user, calls = make_user(SqlUserWrapper)
    user._do_step({"sql": "SELECT * FROM missing"})
    assert_failed(calls, "SQL", "sql", LookupError, "no such table")


def test_sql_step_without_sql_fires_nothing(monkeypatch):
    engines = install_fake_sqlalchemy(monkeypatch)
    user, calls = make_user(SqlUserWrapper)
    user._do_step({"method": "execute", "name": "empty"})
    assert calls == []
    assert engines == []


def test_sql_engine_requires_sqlalchemy(monkeypatch):
    hide_module(monkeypatch, "sqlalchemy")
    user, _ = make_user(SqlUserWrapper)
    with pytest.raises(RuntimeError, match="SQLAlchemy is required"):
        user._ensure_engine()


# ---------------------------------------------------------------------------
# SSE
# ---------------------------------------------------------------------------

class FakeSseResponse:
    def __init__(self, lines, close_error=None):
        self.lines = lines
        self.close_error = close_error
        self.closed = False

    def iter_lines(self, decode_unicode=False):
        assert decode_unicode is True
        return iter(self.lines)

    def close(self):
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


def install_fake_requests(monkeypatch, response):
    seen = []

    def get(url, headers=None, stream=False, timeout=None):
        seen.append({"url": url, "headers": headers, "stream": stream, "timeout": timeout})
        return response

    fake_module(monkeypatch, "requests", get=get)
    return seen


def test_sse_open_streams_with_event_stream_accept(monkeypatch):
    seen = install_fake_requests(monkeypatch, FakeSseResponse([]))
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open", "request_url": "https://api/stream", "headers": {"X-A": "1"}, "timeout": 4})
    event = assert_ok(calls, "SSE", "https://api/stream", 0)
    assert event["url"] == "https://api/stream"
    assert seen == [{
        "url": "https://api/stream",
        "headers": {"X-A": "1", "Accept": "text/event-stream"},
        "stream": True,
        "timeout": 4.0,
    }]


def test_sse_connect_alias_keeps_explicit_accept(monkeypatch):
    seen = install_fake_requests(monkeypatch, FakeSseResponse([]))
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "connect", "url": "https://s", "headers": {"Accept": "*/*"}, "name": "c"})
    assert_ok(calls, "SSE", "c", 0)
    assert seen[0]["headers"] == {"Accept": "*/*"}


def test_sse_wait_counts_until_expected_event(monkeypatch):
    lines = ["event: ping", "data: warmup", "", "data: ready now", "", "data: later", ""]
    install_fake_requests(monkeypatch, FakeSseResponse(lines))
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open", "request_url": "https://s"})
    calls.clear()
    user._do_step({"method": "wait", "expect": "ready", "name": "w"})
    expected = len("ping") + len("warmup") + len("ready now")
    event = assert_ok(calls, "SSE", "w", expected)
    assert event["url"] == "https://s"


def test_sse_wait_without_expect_returns_first_event(monkeypatch):
    install_fake_requests(monkeypatch, FakeSseResponse(["data: one", "", "data: two", ""]))
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open", "request_url": "https://s"})
    calls.clear()
    user._do_step({"name": "default-wait"})
    assert_ok(calls, "SSE", "default-wait", 3)


def test_sse_wait_before_open_fails(monkeypatch):
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "wait", "name": "w"})
    assert_failed(calls, "SSE", "w", RuntimeError, "not open")


def test_sse_wait_stream_end_fails(monkeypatch):
    install_fake_requests(monkeypatch, FakeSseResponse(["data: nope", ""]))
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open", "request_url": "https://s"})
    calls.clear()
    user._do_step({"method": "wait", "expect": "ready", "name": "w"})
    assert_failed(calls, "SSE", "w", RuntimeError, "ended before expected event")


def test_sse_wait_past_deadline_times_out(monkeypatch):
    install_fake_requests(monkeypatch, FakeSseResponse(["data: a", "", "data: ready", ""]))
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open", "request_url": "https://s"})
    calls.clear()
    user._do_step({"method": "wait", "expect": "ready", "timeout": -1, "name": "w"})
    assert_failed(calls, "SSE", "w", TimeoutError, "ready")


@pytest.mark.parametrize("close_error", [None, OSError("already closed")])
def test_sse_close_releases_stream(monkeypatch, close_error):
    response = FakeSseResponse([], close_error=close_error)
    install_fake_requests(monkeypatch, response)
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open", "request_url": "https://s"})
    calls.clear()
    user._do_step({"method": "close", "name": "bye"})
    assert_ok(calls, "SSE", "bye", 0)
    assert response.closed is True
    assert user._response is None


def test_sse_unknown_method_fires_failure():
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "subscribe", "name": "s"})
    assert_failed(calls, "SSE", "s", ValueError, "unsupported sse method")


def test_sse_request_error_is_reported(monkeypatch):
    def get(*args, **kwargs):
        raise ConnectionError("dns failure")

    fake_module(monkeypatch, "requests", get=get)
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open", "request_url": "https://s"})
    assert_failed(calls, "SSE", "https://s", ConnectionError, "dns failure")
    assert user._response is None


# ---------------------------------------------------------------------------
# Thrift
# ---------------------------------------------------------------------------

class FakeThriftClient:
    def __init__(self, close_error=None):
        self.calls = []
        self.closed = False
        self.close_error = close_error

    def add(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return sum(args) + sum(kwargs.values())

    def fail(self):
        raise ArithmeticError("server blew up")

    def close(self):
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


def install_fake_thriftpy(monkeypatch, client):
    record = {}
    service = object()

    def load(path):
        record["load"] = path
        return SimpleNamespace(Calculator=service)

    def make_client(svc, host=None, port=None):
        record["make_client"] = (svc, host, port)
        return client

    rpc = fake_module(monkeypatch, "thriftpy2.rpc", make_client=make_client)
    fake_module(monkeypatch, "thriftpy2", load=load, rpc=rpc)
    record["service"] = service
    return record


def test_thrift_connect_loads_idl_and_makes_client(monkeypatch):
    client = FakeThriftClient()
    record = install_fake_thriftpy(monkeypatch, client)
    user, calls = make_user(ThriftUserWrapper)
    user._do_step({"method": "connect", "thrift_file": "calc.thrift", "service": "Calculator", "port": "9091"})
    assert_ok(calls, "THRIFT", "connect", 0)
    assert record["load"] == "calc.thrift"
    assert record["make_client"] == (record["service"], "127.0.0.1", 9091)
    assert user._client is client


def test_thrift_call_passes_args_and_measures_result():
    user, calls = make_user(ThriftUserWrapper)
    client = FakeThriftClient()
    user._client = client
    user._do_step({"method": "call", "function": "add", "args": [40, 2], "kwargs": {"bonus": 100}})
    assert client.calls == [((40, 2), {"bonus": 100})]
    assert_ok(calls, "THRIFT", "add", len("142"))


def test_thrift_call_requires_connection():
    user, calls = make_user(ThriftUserWrapper)
    user._do_step({"method": "call", "function": "add"})
    assert_failed(calls, "THRIFT", "add", RuntimeError, "not connected")


def test_thrift_call_server_error_is_reported():
    user, calls = make_user(ThriftUserWrapper)
    user._client = FakeThriftClient()
    user._do_step({"method": "call", "function": "fail", "name": "f"})
    assert_failed(calls, "THRIFT", "f", ArithmeticError, "blew up")


@pytest.mark.parametrize("close_error", [None, OSError("broken pipe")])
def test_thrift_close_always_drops_client(close_error):
    user, calls = make_user(ThriftUserWrapper)
    client = FakeThriftClient(close_error=close_error)
    user._client = client
    user._do_step({"method": "close"})
    assert client.closed is True
    assert user._client is None
    if close_error is None:
        assert_ok(calls, "THRIFT", "close", 0)
    else:
        assert_failed(calls, "THRIFT", "close", OSError, "broken pipe")


def test_thrift_missing_library_reports_runtime_error(monkeypatch):
    hide_module(monkeypatch, "thriftpy2", "thriftpy2.rpc")
    user, calls = make_user(ThriftUserWrapper)
    user._do_step({"method": "connect", "thrift_file": "a.thrift", "service": "S"})
    assert_failed(calls, "THRIFT", "connect", RuntimeError, "thriftpy2 is required")


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method, http_method, payload, expected_length", [
    ("read", "GET", b'{"data": 1}', len(b'{"data": 1}')),
    ("list", "LIST", b'{"keys": []}', len(b'{"keys": []}')),
    ("delete", "DELETE", b"", 0),
])
def test_vault_read_list_delete(monkeypatch, method, http_method, payload, expected_length):
    seen = install_urlopen(monkeypatch, payload=payload)
    user, calls = make_user(VaultUserWrapper)
    user._do_step({"method": method, "addr": "https://vault:8200/", "path": "/secret/app", "token": "t0k"})
    assert_ok(calls, "VAULT", method, expected_length)
    request = seen[0]["request"]
    assert request.get_method() == http_method
    assert request.full_url == "https://vault:8200/v1/secret/app"
    assert request.get_header("X-vault-token") == "t0k"
    assert request.data is None
    assert seen[0]["timeout"] == 5.0


def test_vault_write_posts_json_body_without_token(monkeypatch):
    seen = install_urlopen(monkeypatch, payload=b"{}")
    user, calls = make_user(VaultUserWrapper)
    data = {"data": {"k": "v"}}
    user._do_step({"method": "write", "path": "secret/data/app", "data": data, "timeout": 1, "name": "put"})
    body = json.dumps(data).encode("utf-8")
    assert_ok(calls, "VAULT", "put", len(body))
    request = seen[0]["request"]
    assert request.get_method() == "POST"
    assert request.full_url == "https://127.0.0.1:8200/v1/secret/data/app"
    assert request.data == body
    assert request.get_header("X-vault-token") is None
    assert request.get_header("Content-type") == "application/json"
    assert seen[0]["timeout"] == 1.0


def test_vault_http_error_is_reported(monkeypatch):
    error = urllib.error.HTTPError("https://v", 403, "permission denied", {}, None)
    install_urlopen(monkeypatch, error=error)
    user, calls = make_user(VaultUserWrapper)
    user._do_step({"method": "read", "path": "secret/x"})
    assert_failed(calls, "VAULT", "read", urllib.error.HTTPError, "403")


def test_vault_missing_path_fails_without_request(monkeypatch):
    seen = install_urlopen(monkeypatch)
    user, calls = make_user(VaultUserWrapper)
    user._do_step({"method": "read"})
    assert_failed(calls, "VAULT", "read", KeyError, "path")
    assert seen == []


# ---------------------------------------------------------------------------
# WebPush
# ---------------------------------------------------------------------------

def install_fake_pywebpush(monkeypatch, text="", error=None):
    seen = []

    def webpush(**kwargs):
        seen.append(kwargs)
        if error is not None:
            raise error
        return SimpleNamespace(text=text)

    fake_module(monkeypatch, "pywebpush", webpush=webpush)
    return seen


def test_webpush_send_serialises_payload(monkeypatch):
    seen = install_fake_pywebpush(monkeypatch, text="created")
    user, calls = make_user(WebPushUserWrapper)
    subscription = {"endpoint": "https://push/x", "keys": {"p256dh": "a", "auth": "b"}}
    user._do_step({
        "method": "send", "subscription": subscription, "data": {"msg": "hi"},
        "vapid_private_key": "key", "vapid_claims": {"sub": "mailto:o@x"}, "ttl": "30",
    })
    assert_ok(calls, "WEBPUSH", "send", len("created"))
    assert seen == [{
        "subscription_info": subscription,
        "data": json.dumps({"msg": "hi"}),
        "vapid_private_key": "key",
        "vapid_claims": {"sub": "mailto:o@x"},
        "ttl": 30,
    }]


def test_webpush_send_defaults(monkeypatch):
    seen = install_fake_pywebpush(monkeypatch, text=None)
    user, calls = make_user(WebPushUserWrapper)
    user._do_step({"method": "send", "subscription": {"endpoint": "e"}, "data": "plain", "name": "push"})
    assert_ok(calls, "WEBPUSH", "push", 0)
    assert seen[0]["data"] == "plain"
    assert seen[0]["vapid_claims"] == {}
    assert seen[0]["vapid_private_key"] is None
    assert seen[0]["ttl"] == 60


def test_webpush_client_error_is_reported(monkeypatch):
    install_fake_pywebpush(monkeypatch, error=ConnectionError("410 gone"))
    user, calls = make_user(WebPushUserWrapper)
    user._do_step({"method": "send", "subscription": {"endpoint": "e"}})
    assert_failed(calls, "WEBPUSH", "send", ConnectionError, "410 gone")


def test_webpush_missing_subscription_fails(monkeypatch):
    seen = install_fake_pywebpush(monkeypatch)
    user, calls = make_user(WebPushUserWrapper)
    user._do_step({"method": "send"})
    assert_failed(calls, "WEBPUSH", "send", KeyError, "subscription")
    assert seen == []


def test_webpush_missing_library_reports_runtime_error(monkeypatch):
    hide_module(monkeypatch, "pywebpush")
    user, calls = make_user(WebPushUserWrapper)
    user._do_step({"method": "send", "subscription": {}})
    assert_failed(calls, "WEBPUSH", "send", RuntimeError, "pywebpush is required")


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

class FakeWs:
    def __init__(self, url, replies=()):
        self.url = url
        self.replies = list(replies)
        self.sent = []
        self.timeouts = []
        self.closed = False

    def send(self, payload):
        self.sent.append(payload)

    def settimeout(self, value):
        self.timeouts.append(value)

    def recv(self):
        return self.replies.pop(0)

    def close(self):
        self.closed = True


def install_fake_websocket(monkeypatch, replies=()):
    created = []

    def create_connection(url, timeout=None):
        ws = FakeWs(url, replies)
        ws.connect_timeout = timeout
        created.append(ws)
        return ws

    fake_module(monkeypatch, "websocket", create_connection=create_connection)
    return created


def test_websocket_connect_is_idempotent_per_url(monkeypatch):
    created = install_fake_websocket(monkeypatch)
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "connect", "request_url": "ws://a", "timeout": 3})
    user._do_step({"method": "connect", "request_url": "ws://a"})
    user._do_step({"method": "connect", "request_url": "ws://b", "name": "switch"})
    assert [ws.url for ws in created] == ["ws://a", "ws://b"]
    assert created[0].connect_timeout == 3.0
    assert created[0].closed is True
    assert created[1].closed is False
    assert [c["name"] for c in calls] == ["ws://a", "ws://a", "switch"]
    assert all(c["request_type"] == "WS" and c["exception"] is None for c in calls)
    assert calls[-1]["url"] == "ws://b"


def test_websocket_send_auto_connects(monkeypatch):
    created = install_fake_websocket(monkeypatch)
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"request_url": "ws://h/feed", "payload": "hello", "name": "greet"})
    assert_ok(calls, "WS", "greet", 5)
    assert created[0].sent == ["hello"]


def test_websocket_recv_checks_expectation(monkeypatch):
    install_fake_websocket(monkeypatch, replies=[b"welcome", "nothing useful"])
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "recv", "request_url": "ws://h", "expect": "come", "timeout": 2, "name": "r1"})
    assert_ok(calls, "WS", "r1", len(b"welcome"))
    assert user._ws.timeouts == [2.0]
    calls.clear()
    user._do_step({"method": "recv", "expect": "welcome", "name": "r2"})
    assert_failed(calls, "WS", "r2", AssertionError, "welcome")


def test_websocket_sendrecv_counts_both_directions(monkeypatch):
    created = install_fake_websocket(monkeypatch, replies=["pong!"])
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "sendrecv", "request_url": "ws://h", "payload": "ping", "expect": "pong"})
    assert_ok(calls, "WS", "ws://h", 4 + 5)
    assert created[0].sent == ["ping"]


def test_websocket_close_then_send_reconnects_to_last_url(monkeypatch):
    created = install_fake_websocket(monkeypatch)
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "connect", "request_url": "ws://h"})
    user._do_step({"method": "close"})
    assert created[0].closed is True
    assert user._ws is None
    user._do_step({"method": "send", "payload": "again"})
    assert len(created) == 2
    assert created[1].sent == ["again"]
    assert [c["exception"] for c in calls] == [None, None, None]


def test_websocket_send_without_url_fails():
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "send", "payload": "x", "name": "s"})
    assert_failed(calls, "WS", "s", RuntimeError, "not established")


def test_websocket_unknown_method_fires_failure(monkeypatch):
    install_fake_websocket(monkeypatch)
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "ping", "request_url": "ws://h"})
    assert_failed(calls, "WS", "ws://h", ValueError, "unsupported websocket method")


def test_websocket_connection_error_is_reported(monkeypatch):
    def create_connection(url, timeout=None):
        raise ConnectionRefusedError("refused")

    fake_module(monkeypatch, "websocket", create_connection=create_connection)
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "connect", "request_url": "ws://h"})
    assert_failed(calls, "WS", "ws://h", ConnectionRefusedError, "refused")
    assert user._ws is None


def test_websocket_missing_library_reports_runtime_error(monkeypatch):
    hide_module(monkeypatch, "websocket")
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "connect", "request_url": "ws://h"})
    assert_failed(calls, "WS", "ws://h", RuntimeError, "websocket-client is required")


# ---------------------------------------------------------------------------
# ZeroMQ
# ---------------------------------------------------------------------------

class FakeZmqSocket:
    def __init__(self, kind="REQ", poll_result=1, reply=b""):
        self.kind = kind
        self.poll_result = poll_result
        self.reply = reply
        self.connected = []
        self.bound = []
        self.sent = []
        self.options = []
        self.polls = []
        self.linger = None

    def connect(self, endpoint):
        self.connected.append(endpoint)

    def bind(self, endpoint):
        self.bound.append(endpoint)

    def send(self, payload):
        self.sent.append(payload)

    def poll(self, timeout, flags):
        self.polls.append((timeout, flags))
        return self.poll_result

    def recv(self):
        return self.reply

    def setsockopt(self, option, value):
        self.options.append((option, value))

    def close(self, linger=None):
        self.linger = linger


def install_fake_zmq(monkeypatch):
    sockets = []

    class Context:
        @classmethod
        def instance(cls):
            return cls()

        def socket(self, kind):
            sock = FakeZmqSocket(kind)
            sockets.append(sock)
            return sock

    fake_module(monkeypatch, "zmq", Context=Context, REQ="REQ", SUB="SUB", POLLIN="POLLIN", SUBSCRIBE="SUBSCRIBE")
    return sockets


def test_zmq_connect_and_bind(monkeypatch):
    sockets = install_fake_zmq(monkeypatch)
    user, calls = make_user(ZmqUserWrapper)
    user._do_step({"method": "connect", "endpoint": "tcp://h:1"})
    user._do_step({"method": "connect", "socket_type": "SUB", "bind": True, "name": "bind"})
    assert sockets[0].kind == "REQ"
    assert sockets[0].connected == ["tcp://h:1"]
    assert sockets[1].kind == "SUB"
    assert sockets[1].bound == ["tcp://127.0.0.1:5555"]
    assert [c["name"] for c in calls] == ["connect", "bind"]
    assert all(c["request_type"] == "ZMQ" and c["exception"] is None for c in calls)


def test_zmq_send_encodes_payload():
    user, calls = make_user(ZmqUserWrapper)
    sock = FakeZmqSocket()
    user._socket = sock
    user._do_step({"method": "send", "payload": "héllo"})
    assert sock.sent == ["héllo".encode("utf-8")]
    assert_ok(calls, "ZMQ", "send", len("héllo".encode("utf-8")))


def test_zmq_recv_polls_then_reads(monkeypatch):
    install_fake_zmq(monkeypatch)
    user, calls = make_user(ZmqUserWrapper)
    sock = FakeZmqSocket(reply=b"world")
    user._socket = sock
    user._do_step({"method": "recv", "timeout_ms": "250"})
    assert sock.polls == [(250, "POLLIN")]
    assert_ok(calls, "ZMQ", "recv", 5)


def test_zmq_recv_timeout_fails(monkeypatch):
    install_fake_zmq(monkeypatch)
    user, calls = make_user(ZmqUserWrapper)
    user._socket = FakeZmqSocket(poll_result=0)
    user._do_step({"method": "recv", "name": "r"})
    assert_failed(calls, "ZMQ", "r", TimeoutError, "zmq recv timeout")


@pytest.mark.parametrize("method", ["send", "recv", "subscribe"])
def test_zmq_requires_open_socket(monkeypatch, method):
    install_fake_zmq(monkeypatch)
    user, calls = make_user(ZmqUserWrapper)
    user._do_step({"method": method})
    assert_failed(calls, "ZMQ", method, RuntimeError, "zmq socket not open")


def test_zmq_close_drops_socket_and_is_idempotent():
    user, calls = make_user(ZmqUserWrapper)
    sock = FakeZmqSocket()
    user._socket = sock
    user._context = object()
    user._do_step({"method": "close"})
    user._do_step({"method": "close"})
    assert sock.linger == 0
    assert user._socket is None
    assert user._context is None
    assert [c["exception"] for c in calls] == [None, None]


def test_zmq_unknown_socket_type_fails(monkeypatch):
    install_fake_zmq(monkeypatch)
    user, calls = make_user(ZmqUserWrapper)
    user._do_step({"method": "connect", "socket_type": "NOPE"})
    assert_failed(calls, "ZMQ", "connect", AttributeError, "NOPE")


def test_zmq_missing_library_reports_runtime_error(monkeypatch):
    hide_module(monkeypatch, "zmq")
    user, calls = make_user(ZmqUserWrapper)
    user._do_step({"method": "connect"})
    assert_failed(calls, "ZMQ", "connect", RuntimeError, "pyzmq is required")


# ---------------------------------------------------------------------------
# scenario_runner
# ---------------------------------------------------------------------------

@pytest.fixture
def executed(monkeypatch):
    log = []

    def fake_execute(method_map, task):
        log.append(task.get("name") or task.get("method"))
        if task.get("boom"):
            raise task["boom"]

    monkeypatch.setattr(scenario_runner, "execute_task", fake_execute)
    monkeypatch.setattr(network_conditioner, "_INSTALLED", None)
    return log


def test_scenario_runs_list_in_order_with_method_map(monkeypatch):
    seen = []
    method_map = {"get": object()}
    monkeypatch.setattr(scenario_runner, "execute_task", lambda mm, task: seen.append((mm, task["name"])))
    monkeypatch.setattr(network_conditioner, "_INSTALLED", None)
    scenario_runner.run_scenario(method_map, [{"name": "a"}, "junk", {"name": "b"}])
    assert seen == [(method_map, "a"), (method_map, "b")]


def test_scenario_accepts_legacy_dict_form(executed):
    scenario_runner.run_scenario({}, {"get": {"request_url": "/a"}, "post": {"request_url": "/b"}})
    assert executed == ["get", "post"]


@pytest.mark.parametrize("mode", ["sequence", "conditional", "SEQUENCE"])
def test_scenario_wrapped_payload_runs_every_task(executed, mode):
    scenario_runner.run_scenario({}, {"mode": mode, "tasks": [{"name": "a"}, {"name": "b"}, {"name": "c"}]})
    assert executed == ["a", "b", "c"]


@pytest.mark.parametrize("payload", [None, [], {"tasks": []}, "text"])
def test_scenario_empty_payload_runs_nothing(executed, payload):
    scenario_runner.run_scenario({}, payload)
    assert executed == []


def test_scenario_failing_step_does_not_stop_the_rest(executed):
    scenario_runner.run_scenario({}, [{"name": "a", "boom": ValueError("x")}, {"name": "b"}])
    assert executed == ["a", "b"]


def test_scenario_run_if_and_skip_if(executed):
    parameter_resolver.register_variable("state", "ok")
    parameter_resolver.register_variable("role", "admin")
    tasks = [
        {"name": "eq", "run_if": {"equals": ["${var.state}", "ok"]}},
        {"name": "neq", "run_if": {"not_equals": ["${var.state}", "ok"]}},
        {"name": "in", "run_if": {"in": ["${var.role}", ["admin", "root"]]}},
        {"name": "skipped", "skip_if": {"EQUALS": ["${var.role}", "admin"]}},
        {"name": "kept", "skip_if": {"truthy": ""}},
        {"name": "bool-false", "run_if": False},
        {"name": "int-true", "run_if": 1},
        {"name": "bad-pair", "run_if": {"equals": ["only-one"]}},
        {"name": "unknown-op", "run_if": {"matches": ["a", "a"]}},
        {"name": "list-cond", "run_if": ["a"]},
        {"name": "string-true", "run_if": "${var.state}"},
    ]
    scenario_runner.run_scenario({}, tasks)
    assert executed == ["eq", "in", "kept", "int-true", "string-true"]


def test_scenario_weighted_runs_exactly_one_pick(executed, monkeypatch):
    picks = iter([0, 1, 3])
    bounds = []

    def randbelow(total):
        bounds.append(total)
        return next(picks)

    monkeypatch.setattr(scenario_runner.secrets, "randbelow", randbelow)
    payload = {"mode": "weighted", "tasks": [{"name": "light", "weight": 1}, {"name": "heavy", "weight": 3}]}
    for _ in range(3):
        scenario_runner.run_scenario({}, payload)
    assert executed == ["light", "heavy", "heavy"]
    assert bounds == [4, 4, 4]


def test_scenario_weighted_respects_conditions_and_negative_weights(executed, monkeypatch):
    monkeypatch.setattr(scenario_runner.secrets, "randbelow", lambda total: 0)
    scenario_runner.run_scenario({}, {"mode": "weighted", "tasks": [{"name": "a", "run_if": False}]})
    scenario_runner.run_scenario({}, {"mode": "weighted", "tasks": [{"name": "b", "weight": -2}]})
    assert executed == []


def test_scenario_throttle_acquired_before_execute(executed, monkeypatch):
    order = []
    throttles = []

    class Throttle:
        def acquire(self):
            order.append("acquire")

    def get_throttle(key, rps, burst=None):
        throttles.append((key, rps, burst))
        return Throttle()

    monkeypatch.setattr(scenario_runner, "get_throttle", get_throttle)
    monkeypatch.setattr(scenario_runner, "execute_task", lambda mm, task: order.append(task["name"]))
    scenario_runner.run_scenario({}, [
        {"name": "keyed", "throttle": {"rps": "5", "key": "shared", "burst": "2"}},
        {"name": "by-name", "throttle": {"rps": 1}},
        {"throttle": {"rps": 1}, "name": ""},
        {"name": "no-rps", "throttle": {"burst": 1}},
        {"name": "bad-rps", "throttle": {"rps": "fast"}},
    ])
    assert throttles == [("shared", 5.0, 2), ("by-name", 1.0, None), ("default", 1.0, None)]
    assert order == ["acquire", "keyed", "acquire", "by-name", "acquire", "", "no-rps", "bad-rps"]


def test_scenario_think_time_sleeps_after_each_step(executed, monkeypatch):
    sleeps = []
    monkeypatch.setattr(scenario_runner.time, "sleep", lambda s: sleeps.append((s, list(executed))))
    scenario_runner.run_scenario({}, [
        {"name": "a", "think_time": 0.25},
        {"name": "b"},
        {"name": "c", "think_time": 1, "boom": ValueError("x")},
    ])
    assert sleeps == [(0.25, ["a"]), (1.0, ["a", "b", "c"])]


def test_scenario_retry_policy_retries_transient_errors(monkeypatch):
    attempts = []

    def flaky_execute(method_map, task):
        attempts.append(task["name"])
        if len(attempts) < 3:
            raise ConnectionError("reset")

    monkeypatch.setattr(scenario_runner, "execute_task", flaky_execute)
    monkeypatch.setattr(network_conditioner, "_INSTALLED", None)
    retry = {"transient": 5, "base_delay": 0, "jitter": 0}
    scenario_runner.run_scenario({}, [{"name": "r", "retry": retry}])
    assert attempts == ["r", "r", "r"]


def test_scenario_retry_does_not_repeat_permanent_errors(executed):
    retry = {"base_delay": 0, "jitter": 0}
    scenario_runner.run_scenario({}, [{"name": "p", "retry": retry, "boom": ValueError("bad")}, {"name": "next"}])
    assert executed == ["p", "next"]


def test_scenario_network_conditioner_drops_matching_steps(executed, monkeypatch):
    conditioner = network_conditioner.NetworkConditioner(loss_rate=1.0, name_filter="flaky")
    monkeypatch.setattr(network_conditioner, "_INSTALLED", conditioner)
    scenario_runner.run_scenario({}, [{"name": "flaky-call"}, {"name": "stable"}])
    assert executed == ["stable"]


def test_sql_missing_sqlalchemy_reports_the_clear_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "sqlalchemy", None)
    user, calls = make_user(SqlUserWrapper)
    user._do_step({"sql": "SELECT 1"})
    assert_failed(calls, "SQL", "sql", RuntimeError, "SQLAlchemy is required")
