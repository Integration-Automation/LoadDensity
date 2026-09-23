"""
Settings passed to a template's ``set_wrapper_*`` setter act as step defaults.

``host`` is the default target of the socket, SSE, WebSocket and MQTT templates; ``connection``
supplies default step fields to the SMTP, SNMP, SOAP, Thrift, Vault, WebPush and ZeroMQ templates.
A value named in the step always wins. Client libraries are in-memory fakes.
"""

import sys
import types
import urllib.request
from types import SimpleNamespace

import pytest

from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template import smtp_user_template as smtp_mod
from je_load_density.wrapper.user_template import socket_user_template as socket_mod
from je_load_density.wrapper.user_template.mqtt_user_template import MqttUserWrapper, set_wrapper_mqtt_user
from je_load_density.wrapper.user_template.smtp_user_template import SmtpUserWrapper, set_wrapper_smtp_user
from je_load_density.wrapper.user_template.snmp_user_template import SnmpUserWrapper, set_wrapper_snmp_user
from je_load_density.wrapper.user_template.soap_user_template import SoapUserWrapper, set_wrapper_soap_user
from je_load_density.wrapper.user_template.socket_user_template import SocketUserWrapper, set_wrapper_socket_user
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


def make_user(cls):
    env = SimpleNamespace(events=SimpleNamespace(request=FakeRequestEvent()))
    return cls(env), env.events.request.calls


def assert_all_ok(calls, count):
    assert len(calls) == count, calls
    assert all(call["exception"] is None for call in calls), calls


def fake_module(monkeypatch, name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def configure(monkeypatch, key, setter, **settings):
    """Give ``key`` a fresh proxy for the test, then configure it through the public setter."""
    fresh = type(locust_wrapper_proxy.user_dict[key])()
    monkeypatch.setitem(locust_wrapper_proxy.user_dict, key, fresh)
    setter({}, tasks=[], **settings)


@pytest.fixture(autouse=True)
def isolated_resolver(monkeypatch):
    monkeypatch.setattr(parameter_resolver, "_variables", {})
    monkeypatch.setattr(parameter_resolver, "_csv_sources", {})


# ---------------------------------------------------------------------------
# host: socket
# ---------------------------------------------------------------------------

class FakeTcpConn:
    def sendall(self, data):
        self.sent = data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def install_fake_socket(monkeypatch):
    addresses = []

    def create_connection(address, timeout=None):
        addresses.append(address)
        return FakeTcpConn()

    monkeypatch.setattr(socket_mod, "socket", SimpleNamespace(create_connection=create_connection))
    return addresses


def test_socket_uses_setter_host_as_default_target(monkeypatch):
    addresses = install_fake_socket(monkeypatch)
    configure(monkeypatch, "socket_user", set_wrapper_socket_user, host="10.0.0.5:7000")
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"payload": "x"})
    assert_all_ok(calls, 1)
    assert addresses == [("10.0.0.5", 7000)]
    assert calls[0]["url"] == "10.0.0.5:7000"


def test_socket_step_target_overrides_setter_host(monkeypatch):
    addresses = install_fake_socket(monkeypatch)
    configure(monkeypatch, "socket_user", set_wrapper_socket_user, host="10.0.0.5:7000")
    user, calls = make_user(SocketUserWrapper)
    user._do_step({"target": "step:1", "payload": "x"})
    user._do_step({"host": "step-host:2", "payload": "x"})
    user._do_step({"payload": "x"})
    assert_all_ok(calls, 3)
    assert addresses == [("step", 1), ("step-host", 2), ("10.0.0.5", 7000)]


# ---------------------------------------------------------------------------
# host: SSE
# ---------------------------------------------------------------------------

def install_fake_requests(monkeypatch):
    urls = []

    def get(url, headers=None, stream=False, timeout=None):
        urls.append(url)
        return SimpleNamespace(close=lambda: None)

    fake_module(monkeypatch, "requests", get=get)
    return urls


def test_sse_uses_setter_host_as_default_url(monkeypatch):
    urls = install_fake_requests(monkeypatch)
    configure(monkeypatch, "sse_user", set_wrapper_sse_user, host="https://events.example/stream")
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open"})
    assert_all_ok(calls, 1)
    assert urls == ["https://events.example/stream"]
    assert calls[0]["name"] == "https://events.example/stream"


def test_sse_step_url_overrides_setter_host(monkeypatch):
    urls = install_fake_requests(monkeypatch)
    configure(monkeypatch, "sse_user", set_wrapper_sse_user, host="https://events.example/stream")
    user, calls = make_user(SseUserWrapper)
    user._do_step({"method": "open"})
    user._do_step({"method": "open", "request_url": "https://step/a"})
    user._do_step({"method": "open", "url": "https://step/b"})
    assert_all_ok(calls, 3)
    assert urls == ["https://events.example/stream", "https://step/a", "https://step/b"]


# ---------------------------------------------------------------------------
# host: WebSocket
# ---------------------------------------------------------------------------

class FakeWs:
    def __init__(self, url):
        self.url = url
        self.sent = []

    def send(self, payload):
        self.sent.append(payload)

    def close(self):
        self.closed = True


def install_fake_websocket(monkeypatch):
    created = []

    def create_connection(url, timeout=None):
        created.append(FakeWs(url))
        return created[-1]

    fake_module(monkeypatch, "websocket", create_connection=create_connection)
    return created


def test_websocket_uses_setter_host_as_default_url(monkeypatch):
    created = install_fake_websocket(monkeypatch)
    configure(monkeypatch, "websocket_user", set_wrapper_websocket_user, host="ws://feed.example/live")
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "send", "payload": "hi"})
    assert_all_ok(calls, 1)
    assert [ws.url for ws in created] == ["ws://feed.example/live"]
    assert created[0].sent == ["hi"]


def test_websocket_step_url_overrides_setter_host(monkeypatch):
    created = install_fake_websocket(monkeypatch)
    configure(monkeypatch, "websocket_user", set_wrapper_websocket_user, host="ws://feed.example/live")
    user, calls = make_user(WebSocketUserWrapper)
    user._do_step({"method": "connect"})
    user._do_step({"method": "connect", "request_url": "ws://step/a"})
    user._do_step({"method": "send", "payload": "hi"})
    assert_all_ok(calls, 3)
    assert [ws.url for ws in created] == ["ws://feed.example/live", "ws://step/a"]
    assert created[1].sent == ["hi"]


# ---------------------------------------------------------------------------
# host: MQTT
# ---------------------------------------------------------------------------

def install_fake_paho(monkeypatch):
    connects = []

    class FakeClient:
        def __init__(self, client_id, clean_session):
            self.client_id = client_id

        def connect(self, host, port, keepalive):
            connects.append((host, port))

        def loop_start(self):
            pass

        def loop_stop(self):
            pass

        def disconnect(self):
            pass

    client_module = fake_module(monkeypatch, "paho.mqtt.client", Client=FakeClient)
    mqtt_module = fake_module(monkeypatch, "paho.mqtt", client=client_module)
    fake_module(monkeypatch, "paho", mqtt=mqtt_module)
    return connects


def test_mqtt_uses_setter_host_as_default_broker(monkeypatch):
    connects = install_fake_paho(monkeypatch)
    configure(monkeypatch, "mqtt_user", set_wrapper_mqtt_user, host="broker.example:1999")
    user, calls = make_user(MqttUserWrapper)
    user._do_step({"method": "connect"})
    assert_all_ok(calls, 1)
    assert connects == [("broker.example", 1999)]
    assert calls[0]["url"] == "broker.example:1999"


def test_mqtt_step_broker_overrides_setter_host(monkeypatch):
    connects = install_fake_paho(monkeypatch)
    configure(monkeypatch, "mqtt_user", set_wrapper_mqtt_user, host="broker.example:1999")
    user, calls = make_user(MqttUserWrapper)
    user._do_step({"method": "connect", "broker": "step:1884"})
    user._do_step({"method": "connect", "host": "step-host:1885"})
    user._do_step({"method": "connect"})
    assert_all_ok(calls, 3)
    assert connects == [("step", 1884), ("step-host", 1885), ("broker.example", 1999)]


# ---------------------------------------------------------------------------
# connection: SMTP
# ---------------------------------------------------------------------------

class FakeSmtp:
    def __init__(self, host, port, timeout=None):
        self.args = (host, port, timeout)
        self.logins = []

    def noop(self):
        return (250, b"OK")

    def login(self, username, password):
        self.logins.append((username, password))
        return (235, b"Accepted")


def install_fake_smtplib(monkeypatch):
    monkeypatch.setattr(smtp_mod, "smtplib", SimpleNamespace(SMTP=FakeSmtp, SMTP_SSL=FakeSmtp))


def test_smtp_uses_setter_connection_as_step_defaults(monkeypatch):
    install_fake_smtplib(monkeypatch)
    connection = {"host": "mail.example", "port": 2525, "username": "bot", "password": "pw"}
    configure(monkeypatch, "smtp_user", set_wrapper_smtp_user, connection=connection)
    user, calls = make_user(SmtpUserWrapper)
    user._do_step({"method": "connect"})
    user._do_step({"method": "login"})
    assert_all_ok(calls, 2)
    assert user._client.args == ("mail.example", 2525, 10.0)
    assert user._client.logins == [("bot", "pw")]


def test_smtp_step_fields_override_setter_connection(monkeypatch):
    install_fake_smtplib(monkeypatch)
    configure(monkeypatch, "smtp_user", set_wrapper_smtp_user, connection={"host": "mail.example", "port": 2525})
    user, calls = make_user(SmtpUserWrapper)
    user._do_step({"method": "connect", "host": "step-mail"})
    assert_all_ok(calls, 1)
    assert user._client.args == ("step-mail", 2525, 10.0)


# ---------------------------------------------------------------------------
# connection: SNMP
# ---------------------------------------------------------------------------

def install_fake_pysnmp(monkeypatch):
    recorded = {}

    def make_ctor(label):
        def ctor(*args, **kwargs):
            recorded.setdefault(label, []).append(args)
            return label
        return ctor

    hlapi = fake_module(
        monkeypatch, "pysnmp.hlapi",
        SnmpEngine=make_ctor("SnmpEngine"), CommunityData=make_ctor("CommunityData"),
        UdpTransportTarget=make_ctor("UdpTransportTarget"), ContextData=make_ctor("ContextData"),
        ObjectType=make_ctor("ObjectType"), ObjectIdentity=make_ctor("ObjectIdentity"),
        getCmd=lambda *args: iter([(None, 0, 0, ["x=1"])]), nextCmd=lambda *args, **kwargs: iter([]),
    )
    fake_module(monkeypatch, "pysnmp", hlapi=hlapi)
    return recorded


def test_snmp_uses_setter_connection_as_step_defaults(monkeypatch):
    recorded = install_fake_pysnmp(monkeypatch)
    connection = {"host": "10.0.0.9", "port": 1161, "community": "private"}
    configure(monkeypatch, "snmp_user", set_wrapper_snmp_user, connection=connection)
    user, calls = make_user(SnmpUserWrapper)
    user._do_step({"method": "get", "oid": "1.3.6"})
    assert_all_ok(calls, 1)
    assert recorded["UdpTransportTarget"] == [(("10.0.0.9", 1161),)]
    assert recorded["CommunityData"] == [("private",)]


def test_snmp_step_fields_override_setter_connection(monkeypatch):
    recorded = install_fake_pysnmp(monkeypatch)
    connection = {"host": "10.0.0.9", "port": 1161, "community": "private"}
    configure(monkeypatch, "snmp_user", set_wrapper_snmp_user, connection=connection)
    user, calls = make_user(SnmpUserWrapper)
    user._do_step({"method": "get", "oid": "1.3.6", "host": "10.0.0.1", "community": "public"})
    assert_all_ok(calls, 1)
    assert recorded["UdpTransportTarget"] == [(("10.0.0.1", 1161),)]
    assert recorded["CommunityData"] == [("public",)]


# ---------------------------------------------------------------------------
# connection: SOAP and Vault (both over urllib)
# ---------------------------------------------------------------------------

class FakeHttpResponse:
    def read(self):
        return b"<ok/>"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def install_urlopen(monkeypatch):
    seen = []

    def urlopen(request, timeout=None):
        seen.append({"request": request, "timeout": timeout})
        return FakeHttpResponse()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return seen


def test_soap_uses_setter_connection_as_step_defaults(monkeypatch):
    seen = install_urlopen(monkeypatch)
    connection = {"endpoint": "https://svc.example/soap", "timeout": 3}
    configure(monkeypatch, "soap_user", set_wrapper_soap_user, connection=connection)
    user, calls = make_user(SoapUserWrapper)
    user._do_step({"method": "call", "action": "urn:Ping", "envelope": "<e/>"})
    assert_all_ok(calls, 1)
    assert seen[0]["request"].full_url == "https://svc.example/soap"
    assert seen[0]["timeout"] == 3.0


def test_soap_step_fields_override_setter_connection(monkeypatch):
    seen = install_urlopen(monkeypatch)
    connection = {"endpoint": "https://svc.example/soap", "timeout": 3}
    configure(monkeypatch, "soap_user", set_wrapper_soap_user, connection=connection)
    user, calls = make_user(SoapUserWrapper)
    user._do_step({"method": "call", "endpoint": "https://step/soap", "envelope": "<e/>"})
    assert_all_ok(calls, 1)
    assert seen[0]["request"].full_url == "https://step/soap"
    assert seen[0]["timeout"] == 3.0


def test_vault_uses_setter_connection_as_step_defaults(monkeypatch):
    seen = install_urlopen(monkeypatch)
    connection = {"addr": "https://vault.example:8200", "token": "t0k"}
    configure(monkeypatch, "vault_user", set_wrapper_vault_user, connection=connection)
    user, calls = make_user(VaultUserWrapper)
    user._do_step({"method": "read", "path": "secret/app"})
    assert_all_ok(calls, 1)
    request = seen[0]["request"]
    assert request.full_url == "https://vault.example:8200/v1/secret/app"
    assert request.get_header("X-vault-token") == "t0k"


def test_vault_step_fields_override_setter_connection(monkeypatch):
    seen = install_urlopen(monkeypatch)
    connection = {"addr": "https://vault.example:8200", "token": "t0k"}
    configure(monkeypatch, "vault_user", set_wrapper_vault_user, connection=connection)
    user, calls = make_user(VaultUserWrapper)
    user._do_step({"method": "read", "path": "secret/app", "token": "step-token"})
    assert_all_ok(calls, 1)
    request = seen[0]["request"]
    assert request.full_url == "https://vault.example:8200/v1/secret/app"
    assert request.get_header("X-vault-token") == "step-token"


# ---------------------------------------------------------------------------
# connection: Thrift
# ---------------------------------------------------------------------------

def install_fake_thriftpy(monkeypatch):
    clients = []

    def make_client(service, host=None, port=None):
        clients.append((host, port))
        return SimpleNamespace()

    rpc = fake_module(monkeypatch, "thriftpy2.rpc", make_client=make_client)
    fake_module(monkeypatch, "thriftpy2", load=lambda path: SimpleNamespace(Calculator=object()), rpc=rpc)
    return clients


def test_thrift_uses_setter_connection_as_step_defaults(monkeypatch):
    clients = install_fake_thriftpy(monkeypatch)
    connection = {"host": "rpc.example", "port": 9091, "thrift_file": "calc.thrift", "service": "Calculator"}
    configure(monkeypatch, "thrift_user", set_wrapper_thrift_user, connection=connection)
    user, calls = make_user(ThriftUserWrapper)
    user._do_step({"method": "connect"})
    assert_all_ok(calls, 1)
    assert clients == [("rpc.example", 9091)]


def test_thrift_step_fields_override_setter_connection(monkeypatch):
    clients = install_fake_thriftpy(monkeypatch)
    connection = {"host": "rpc.example", "port": 9091, "thrift_file": "calc.thrift", "service": "Calculator"}
    configure(monkeypatch, "thrift_user", set_wrapper_thrift_user, connection=connection)
    user, calls = make_user(ThriftUserWrapper)
    user._do_step({"method": "connect", "port": 9999})
    assert_all_ok(calls, 1)
    assert clients == [("rpc.example", 9999)]


# ---------------------------------------------------------------------------
# connection: WebPush
# ---------------------------------------------------------------------------

def install_fake_pywebpush(monkeypatch):
    seen = []

    def webpush(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(text="")

    fake_module(monkeypatch, "pywebpush", webpush=webpush)
    return seen


WEBPUSH_CONNECTION = {
    "subscription": {"endpoint": "https://push.example/x"},
    "vapid_private_key": "key",
    "vapid_claims": {"sub": "mailto:ops@example"},
}


def test_webpush_uses_setter_connection_as_step_defaults(monkeypatch):
    seen = install_fake_pywebpush(monkeypatch)
    configure(monkeypatch, "webpush_user", set_wrapper_webpush_user, connection=WEBPUSH_CONNECTION)
    user, calls = make_user(WebPushUserWrapper)
    user._do_step({"method": "send", "data": "hi"})
    assert_all_ok(calls, 1)
    assert seen[0]["subscription_info"] == {"endpoint": "https://push.example/x"}
    assert seen[0]["vapid_private_key"] == "key"
    assert seen[0]["vapid_claims"] == {"sub": "mailto:ops@example"}


def test_webpush_step_fields_override_setter_connection(monkeypatch):
    seen = install_fake_pywebpush(monkeypatch)
    configure(monkeypatch, "webpush_user", set_wrapper_webpush_user, connection=WEBPUSH_CONNECTION)
    user, calls = make_user(WebPushUserWrapper)
    user._do_step({"method": "send", "data": "hi", "subscription": {"endpoint": "https://step/y"}})
    assert_all_ok(calls, 1)
    assert seen[0]["subscription_info"] == {"endpoint": "https://step/y"}
    assert seen[0]["vapid_private_key"] == "key"


# ---------------------------------------------------------------------------
# connection: ZeroMQ
# ---------------------------------------------------------------------------

def install_fake_zmq(monkeypatch):
    sockets = []

    class FakeZmqSocket:
        def __init__(self, kind):
            self.kind = kind
            self.connected = []

        def connect(self, endpoint):
            self.connected.append(endpoint)

    class Context:
        @classmethod
        def instance(cls):
            return cls()

        def socket(self, kind):
            sockets.append(FakeZmqSocket(kind))
            return sockets[-1]

    fake_module(monkeypatch, "zmq", Context=Context, REQ="REQ", DEALER="DEALER")
    return sockets


def test_zmq_uses_setter_connection_as_step_defaults(monkeypatch):
    sockets = install_fake_zmq(monkeypatch)
    connection = {"endpoint": "tcp://queue.example:6000", "socket_type": "DEALER"}
    configure(monkeypatch, "zmq_user", set_wrapper_zmq_user, connection=connection)
    user, calls = make_user(ZmqUserWrapper)
    user._do_step({"method": "connect"})
    assert_all_ok(calls, 1)
    assert sockets[0].kind == "DEALER"
    assert sockets[0].connected == ["tcp://queue.example:6000"]


def test_zmq_step_fields_override_setter_connection(monkeypatch):
    sockets = install_fake_zmq(monkeypatch)
    connection = {"endpoint": "tcp://queue.example:6000", "socket_type": "DEALER"}
    configure(monkeypatch, "zmq_user", set_wrapper_zmq_user, connection=connection)
    user, calls = make_user(ZmqUserWrapper)
    user._do_step({"method": "connect", "endpoint": "tcp://step:1"})
    assert_all_ok(calls, 1)
    assert sockets[0].kind == "DEALER"
    assert sockets[0].connected == ["tcp://step:1"]
