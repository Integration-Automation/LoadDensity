"""
Unit tests for the http3, imap, kafka, ldap, memcached, modbus, mongo, mqtt,
nats, neo4j, opcua, pulsar, redis and sftp user templates.

Every client library is replaced by an in-memory fake injected through
``sys.modules`` (or by patching the stdlib class for IMAP), and the Locust
environment is a tiny stand-in whose ``events.request.fire`` records kwargs.
"""

import imaplib
import json
import sys
import types
from types import SimpleNamespace

import pytest

from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template.http3_user_template import Http3UserWrapper, set_wrapper_http3_user
from je_load_density.wrapper.user_template.imap_user_template import ImapUserWrapper, set_wrapper_imap_user
from je_load_density.wrapper.user_template.kafka_user_template import KafkaUserWrapper, set_wrapper_kafka_user
from je_load_density.wrapper.user_template.ldap_user_template import LdapUserWrapper, set_wrapper_ldap_user
from je_load_density.wrapper.user_template.memcached_user_template import (
    MemcachedUserWrapper,
    set_wrapper_memcached_user,
)
from je_load_density.wrapper.user_template.modbus_user_template import ModbusUserWrapper, set_wrapper_modbus_user
from je_load_density.wrapper.user_template.mongo_user_template import MongoUserWrapper, set_wrapper_mongo_user
from je_load_density.wrapper.user_template.mqtt_user_template import MqttUserWrapper, set_wrapper_mqtt_user
from je_load_density.wrapper.user_template.nats_user_template import NatsUserWrapper, set_wrapper_nats_user
from je_load_density.wrapper.user_template.neo4j_user_template import Neo4jUserWrapper, set_wrapper_neo4j_user
from je_load_density.wrapper.user_template.opcua_user_template import OpcuaUserWrapper, set_wrapper_opcua_user
from je_load_density.wrapper.user_template.pulsar_user_template import PulsarUserWrapper, set_wrapper_pulsar_user
from je_load_density.wrapper.user_template.redis_user_template import RedisUserWrapper, set_wrapper_redis_user
from je_load_density.wrapper.user_template.sftp_user_template import SftpUserWrapper, set_wrapper_sftp_user


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class FakeRequestHook:
    """Records every ``fire(**kwargs)`` call."""

    def __init__(self):
        self.calls = []

    def fire(self, **kwargs):
        self.calls.append(kwargs)


class FakeEnvironment:
    """Just enough of a Locust environment for the templates."""

    def __init__(self):
        self.events = SimpleNamespace(request=FakeRequestHook())


_OPEN_LOOPS = []


def make_user(user_cls):
    user = user_cls(FakeEnvironment())
    loop = getattr(user, "_loop", None)
    if loop is not None:
        # nats / opcua create a private event loop per user; close it after the test.
        _OPEN_LOOPS.append(loop)
    return user


@pytest.fixture(autouse=True)
def _isolate_global_state(monkeypatch):
    """Keep resolver registrations and opened event loops from leaking between tests."""
    monkeypatch.setattr(parameter_resolver, "_variables", {})
    monkeypatch.setattr(parameter_resolver, "_csv_sources", {})
    yield
    while _OPEN_LOOPS:
        _OPEN_LOOPS.pop().close()


def events_of(user):
    return user.environment.events.request.calls


def single_event(user):
    calls = events_of(user)
    assert len(calls) == 1, calls
    event = calls[0]
    assert event["response_time"] >= 0
    return event


def assert_success(user, request_type, name, length=None):
    event = single_event(user)
    assert event["request_type"] == request_type
    assert event["name"] == name
    assert event["exception"] is None
    if length is not None:
        assert event["response_length"] == length
    return event


def assert_failure(user, request_type, name, exc_type, match=None):
    event = single_event(user)
    assert event["request_type"] == request_type
    assert event["name"] == name
    assert isinstance(event["exception"], exc_type), event["exception"]
    assert event["response_length"] == 0
    if match is not None:
        assert match in str(event["exception"])
    return event


def install_module(monkeypatch, dotted_name, **attrs):
    """Register a fake module (and any missing parents) in ``sys.modules``."""
    parts = dotted_name.split(".")
    module = None
    for index in range(1, len(parts) + 1):
        name = ".".join(parts[:index])
        existing = sys.modules.get(name)
        if isinstance(existing, types.ModuleType) and getattr(existing, "__fake__", False):
            module = existing
            continue
        module = types.ModuleType(name)
        module.__fake__ = True
        module.__path__ = []
        monkeypatch.setitem(sys.modules, name, module)
        if index > 1:
            setattr(sys.modules[".".join(parts[:index - 1])], parts[index - 1], module)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def block_module(monkeypatch, name):
    """Make ``import name`` and its submodules raise ImportError regardless of what is installed."""
    monkeypatch.setitem(sys.modules, name, None)
    for loaded in [module for module in sys.modules if module.startswith(name + ".")]:
        monkeypatch.setitem(sys.modules, loaded, None)


def fresh_proxy(monkeypatch, key):
    """Swap in a new proxy instance so configure() does not leak into other tests."""
    proxy = type(locust_wrapper_proxy.user_dict[key])()
    monkeypatch.setitem(locust_wrapper_proxy.user_dict, key, proxy)
    return proxy


class Recorder:
    """Generic fake: every attribute is a callable that records its call."""

    def __init__(self, returns=None, raises=None):
        self.calls = []
        self._returns = returns or {}
        self._raises = raises or {}

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)

        def method(*args, **kwargs):
            self.calls.append((attr, args, kwargs))
            if attr in self._raises:
                raise self._raises[attr]
            return self._returns.get(attr)

        return method

    def names(self):
        return [call[0] for call in self.calls]


# ---------------------------------------------------------------------------
# set_wrapper_* and run_tasks (shared across every template in this group)
# ---------------------------------------------------------------------------

SETTERS = [
    (set_wrapper_http3_user, Http3UserWrapper, "http3_user"),
    (set_wrapper_imap_user, ImapUserWrapper, "imap_user"),
    (set_wrapper_kafka_user, KafkaUserWrapper, "kafka_user"),
    (set_wrapper_ldap_user, LdapUserWrapper, "ldap_user"),
    (set_wrapper_memcached_user, MemcachedUserWrapper, "memcached_user"),
    (set_wrapper_modbus_user, ModbusUserWrapper, "modbus_user"),
    (set_wrapper_mongo_user, MongoUserWrapper, "mongo_user"),
    (set_wrapper_mqtt_user, MqttUserWrapper, "mqtt_user"),
    (set_wrapper_nats_user, NatsUserWrapper, "nats_user"),
    (set_wrapper_neo4j_user, Neo4jUserWrapper, "neo4j_user"),
    (set_wrapper_opcua_user, OpcuaUserWrapper, "opcua_user"),
    (set_wrapper_pulsar_user, PulsarUserWrapper, "pulsar_user"),
    (set_wrapper_redis_user, RedisUserWrapper, "redis_user"),
    (set_wrapper_sftp_user, SftpUserWrapper, "sftp_user"),
]
SETTER_IDS = [case[2] for case in SETTERS]


@pytest.mark.parametrize("setter, wrapper_cls, key", SETTERS, ids=SETTER_IDS)
def test_set_wrapper_configures_proxy_and_registers_sources(monkeypatch, tmp_path, setter, wrapper_cls, key):
    proxy = fresh_proxy(monkeypatch, key)
    csv_file = tmp_path / "rows.csv"
    csv_file.write_text("col\nfirst\nsecond\n", encoding="utf-8")
    detail = {"user": key}
    tasks = [{"method": "connect"}]

    result = setter(
        detail,
        tasks=tasks,
        variables={"tb_token": "abc"},
        csv_sources=[{"name": "tb_src", "file_path": str(csv_file)}],
        note="kept",
    )

    assert result is wrapper_cls
    assert proxy.user_detail_dict is detail
    assert proxy.tasks is tasks
    assert proxy.extra == {"note": "kept"}
    assert parameter_resolver.resolve("${var.tb_token}") == "abc"
    assert parameter_resolver.resolve("${csv.tb_src.col}") == "first"
    assert parameter_resolver.resolve("${csv.tb_src.col}") == "second"


@pytest.mark.parametrize("setter, wrapper_cls, key", SETTERS, ids=SETTER_IDS)
def test_set_wrapper_ignores_malformed_variables_and_csv(monkeypatch, setter, wrapper_cls, key):
    proxy = fresh_proxy(monkeypatch, key)

    assert setter({"user": key}, variables=["not", "a", "dict"], csv_sources={"not": "a list"}) is wrapper_cls
    assert parameter_resolver._variables == {}
    assert parameter_resolver._csv_sources == {}
    assert proxy.tasks is None


@pytest.mark.parametrize("setter, wrapper_cls, key", SETTERS, ids=SETTER_IDS)
def test_run_tasks_dispatches_only_dict_entries(monkeypatch, setter, wrapper_cls, key):
    fresh_proxy(monkeypatch, key)
    setter({"user": key}, tasks={"tasks": [{"method": "a"}, "skip-me", {"method": "b"}]})
    user = make_user(wrapper_cls)
    seen = []
    monkeypatch.setattr(user, "_do_step", seen.append)

    user.run_tasks()

    assert seen == [{"method": "a"}, {"method": "b"}]


@pytest.mark.parametrize("setter, wrapper_cls, key", SETTERS, ids=SETTER_IDS)
@pytest.mark.parametrize("tasks", [None, [], {"tasks": None}, "not-a-list"])
def test_run_tasks_without_usable_tasks_does_nothing(monkeypatch, setter, wrapper_cls, key, tasks):
    fresh_proxy(monkeypatch, key)
    setter({"user": key}, tasks=tasks)
    user = make_user(wrapper_cls)
    seen = []
    monkeypatch.setattr(user, "_do_step", seen.append)

    user.run_tasks()

    assert seen == []
    assert events_of(user) == []


# Templates that silently skip an unknown method (no request event at all).
SILENT_UNKNOWN = [
    ImapUserWrapper, LdapUserWrapper, MemcachedUserWrapper, ModbusUserWrapper, MongoUserWrapper,
    NatsUserWrapper, Neo4jUserWrapper, OpcuaUserWrapper, PulsarUserWrapper, SftpUserWrapper,
]


@pytest.mark.parametrize("wrapper_cls", SILENT_UNKNOWN, ids=lambda cls: cls.__name__)
def test_unknown_method_fires_no_event(wrapper_cls):
    user = make_user(wrapper_cls)
    user._do_step({"method": "no_such_method", "name": "x"})
    assert events_of(user) == []


# (wrapper, blocked top-level module, step, request_type, message fragment)
MISSING_LIBRARY = [
    (Http3UserWrapper, "aioquic", {"method": "get", "request_url": "https://h/x"}, "HTTP/3", "aioquic"),
    (KafkaUserWrapper, "kafka", {"method": "produce", "topic": "t"}, "KAFKA", "kafka-python"),
    (LdapUserWrapper, "ldap3", {"method": "connect"}, "LDAP", "ldap3"),
    (MemcachedUserWrapper, "pymemcache", {"method": "connect"}, "MEMCACHED", "pymemcache"),
    (ModbusUserWrapper, "pymodbus", {"method": "connect"}, "MODBUS", "pymodbus"),
    (MongoUserWrapper, "pymongo", {"method": "find_one"}, "MONGO", "pymongo"),
    (MqttUserWrapper, "paho", {"method": "connect"}, "MQTT", "paho-mqtt"),
    (NatsUserWrapper, "nats", {"method": "connect"}, "NATS", "nats-py"),
    (Neo4jUserWrapper, "neo4j", {"method": "connect"}, "NEO4J", "neo4j"),
    (OpcuaUserWrapper, "asyncua", {"method": "connect"}, "OPC-UA", "asyncua"),
    (PulsarUserWrapper, "pulsar", {"method": "connect"}, "PULSAR", "pulsar-client"),
    (SftpUserWrapper, "paramiko", {"method": "connect"}, "SFTP", "paramiko"),
    (RedisUserWrapper, "redis", {"method": "get", "key": "k"}, "REDIS", "pip install redis"),
]


@pytest.mark.parametrize(
    "wrapper_cls, module, step, request_type, fragment", MISSING_LIBRARY, ids=lambda v: getattr(v, "__name__", None),
)
def test_missing_client_library_reports_clear_runtime_error(monkeypatch, wrapper_cls, module, step, request_type,
                                                            fragment):
    block_module(monkeypatch, module)
    user = make_user(wrapper_cls)

    user._do_step(dict(step, name="step"))

    event = assert_failure(user, request_type, "step", RuntimeError, match=fragment)
    assert "is required" in str(event["exception"])
    assert isinstance(event["exception"].__cause__, ImportError)


# ---------------------------------------------------------------------------
# IMAP
# ---------------------------------------------------------------------------

def install_fake_imap(monkeypatch, raises=None):
    created = []

    def factory(kind):
        def build(host, port):
            client = Recorder(
                returns={"noop": ("OK", [b"noop"]), "search": ("OK", [b"1 2"]), "fetch": ("OK", [b"x"])},
                raises=raises,
            )
            created.append((kind, host, port, client))
            return client
        return build

    monkeypatch.setattr(imaplib, "IMAP4", factory("plain"))
    monkeypatch.setattr(imaplib, "IMAP4_SSL", factory("ssl"))
    return created


def test_imap_connect_plain_defaults(monkeypatch):
    created = install_fake_imap(monkeypatch)
    user = make_user(ImapUserWrapper)

    user._do_step({"method": "CONNECT"})

    assert_success(user, "IMAP", "connect")
    kind, host, port, client = created[0]
    assert (kind, host, port) == ("plain", "127.0.0.1", 143)
    assert client.names() == ["noop"]


def test_imap_full_session_dispatches_each_command(monkeypatch):
    created = install_fake_imap(monkeypatch)
    user = make_user(ImapUserWrapper)
    steps = [
        {"method": "connect", "host": "mail", "port": "993", "ssl": True},
        {"method": "login", "username": "u", "password": "p"},
        {"method": "select", "mailbox": "Archive"},
        {"method": "search", "criteria": "UNSEEN"},
        {"method": "fetch", "msg_id": 7, "spec": "(BODY[])", "name": "grab"},
        {"method": "logout"},
    ]
    for step in steps:
        user._do_step(step)

    kind, host, port, client = created[0]
    assert (kind, host, port) == ("ssl", "mail", 993)
    assert client.calls == [
        ("noop", (), {}),
        ("login", ("u", "p"), {}),
        ("select", ("Archive",), {}),
        ("search", (None, "UNSEEN"), {}),
        ("fetch", ("7", "(BODY[])"), {}),
        ("logout", (), {}),
    ]
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "login", "select", "search", "grab", "logout"]
    assert all(c["request_type"] == "IMAP" and c["exception"] is None for c in calls)
    assert user._client is None


@pytest.mark.parametrize("method", ["login", "select", "search", "fetch"])
def test_imap_command_before_connect_fails(method):
    user = make_user(ImapUserWrapper)
    user._do_step({"method": method})
    assert_failure(user, "IMAP", method, RuntimeError, match="not connected")


def test_imap_logout_without_connection_succeeds_with_zero_length():
    user = make_user(ImapUserWrapper)
    user._do_step({"method": "logout"})
    assert_success(user, "IMAP", "logout", length=0)


def test_imap_server_error_is_reported(monkeypatch):
    imap_error = imaplib.IMAP4.error
    install_fake_imap(monkeypatch, raises={"login": imap_error("bad creds")})
    user = make_user(ImapUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "login", "username": "u", "password": "wrong"})

    assert_failure(user, "IMAP", "login", imap_error, match="bad creds")


def test_imap_logout_clears_client_even_when_server_errors(monkeypatch):
    install_fake_imap(monkeypatch, raises={"logout": OSError("gone")})
    user = make_user(ImapUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "logout"})

    assert_failure(user, "IMAP", "logout", OSError)
    assert user._client is None


# ---------------------------------------------------------------------------
# Kafka
# ---------------------------------------------------------------------------

def install_fake_kafka(monkeypatch, records=(), send_error=None):
    state = SimpleNamespace(producers=[], consumers=[])

    class FakeFuture:
        def __init__(self):
            self.timeouts = []

        def get(self, timeout):
            self.timeouts.append(timeout)
            if send_error is not None:
                raise send_error

    class FakeProducer:
        def __init__(self, bootstrap_servers):
            self.bootstrap_servers = bootstrap_servers
            self.sent = []
            self.flushed = []
            self.closed = False
            self.future = FakeFuture()
            state.producers.append(self)

        def send(self, topic, value, key):
            self.sent.append((topic, value, key))
            return self.future

        def flush(self, timeout):
            self.flushed.append(timeout)

        def close(self):
            self.closed = True

    class FakeConsumer:
        def __init__(self, topic, **kwargs):
            self.topic = topic
            self.kwargs = kwargs
            self.closed = False
            state.consumers.append(self)

        def __iter__(self):
            return iter([SimpleNamespace(value=value) for value in records])

        def close(self):
            self.closed = True

    install_module(monkeypatch, "kafka", KafkaProducer=FakeProducer, KafkaConsumer=FakeConsumer)
    return state


def test_kafka_produce_encodes_value_and_key(monkeypatch):
    state = install_fake_kafka(monkeypatch)
    proxy = fresh_proxy(monkeypatch, "kafka_user")
    proxy.bootstrap_servers = ["b1:9092", "b2:9092"]
    user = make_user(KafkaUserWrapper)

    user._do_step({"method": "produce", "topic": "events", "value": {"n": 1}, "key": "s-1",
                   "timeout": 2, "name": "publish"})

    payload = json.dumps({"n": 1}).encode("utf-8")
    assert_success(user, "KAFKA", "publish", length=len(payload))
    producer = state.producers[0]
    assert producer.bootstrap_servers == ["b1:9092", "b2:9092"]
    assert producer.sent == [("events", payload, b"s-1")]
    assert producer.future.timeouts == [2.0]


def test_kafka_produce_reuses_producer_and_falls_back_to_host(monkeypatch):
    state = install_fake_kafka(monkeypatch)
    fresh_proxy(monkeypatch, "kafka_user")
    user = make_user(KafkaUserWrapper)

    user._do_step({"method": "produce", "topic": "t", "value": b"raw"})
    user._do_step({"method": "produce", "topic": "t", "value": "text"})

    assert len(state.producers) == 1
    assert state.producers[0].bootstrap_servers == [KafkaUserWrapper.host]
    assert state.producers[0].sent == [("t", b"raw", None), ("t", b"text", None)]
    assert [c["response_length"] for c in events_of(user)] == [3, 4]


def test_kafka_produce_broker_error_is_reported(monkeypatch):
    install_fake_kafka(monkeypatch, send_error=TimeoutError("no ack"))
    fresh_proxy(monkeypatch, "kafka_user")
    user = make_user(KafkaUserWrapper)

    user._do_step({"method": "produce", "topic": "t", "value": "v"})

    assert_failure(user, "KAFKA", "produce", TimeoutError, match="no ack")


def test_kafka_consume_returns_first_matching_record(monkeypatch):
    state = install_fake_kafka(monkeypatch, records=[b"other", b"hello world", b"later"])
    fresh_proxy(monkeypatch, "kafka_user")
    user = make_user(KafkaUserWrapper)

    user._do_step({"method": "consume", "topic": "events", "timeout": 1.5, "expect": "hello"})
    user._do_step({"method": "consume", "topic": "events"})

    calls = events_of(user)
    assert [c["exception"] for c in calls] == [None, None]
    assert [c["response_length"] for c in calls] == [len(b"hello world"), len(b"other")]
    assert len(state.consumers) == 1
    consumer = state.consumers[0]
    assert consumer.topic == "events"
    assert consumer.kwargs["consumer_timeout_ms"] == 1500
    assert consumer.kwargs["bootstrap_servers"] == [KafkaUserWrapper.host]


def test_kafka_consume_without_match_times_out(monkeypatch):
    install_fake_kafka(monkeypatch, records=[b"nope"])
    fresh_proxy(monkeypatch, "kafka_user")
    user = make_user(KafkaUserWrapper)

    user._do_step({"method": "consume", "topic": "events", "expect": "hello"})

    assert_failure(user, "KAFKA", "consume", TimeoutError, match="events")


def test_kafka_flush_and_close_release_clients(monkeypatch):
    state = install_fake_kafka(monkeypatch, records=[b"x"])
    fresh_proxy(monkeypatch, "kafka_user")
    user = make_user(KafkaUserWrapper)
    user._do_step({"method": "produce", "topic": "t", "value": "v"})
    user._do_step({"method": "consume", "topic": "t"})
    events_of(user).clear()

    user._do_step({"method": "flush", "timeout": 3})
    user._do_step({"method": "close"})

    assert [c["exception"] for c in events_of(user)] == [None, None]
    assert state.producers[0].flushed == [3.0]
    assert state.producers[0].closed is True
    assert state.consumers[0].closed is True
    assert user._producer is None and user._consumers == {}


def test_kafka_flush_without_producer_is_a_noop_success():
    user = make_user(KafkaUserWrapper)
    user._do_step({"method": "flush"})
    assert_success(user, "KAFKA", "flush", length=0)


def test_kafka_unknown_method_fires_value_error():
    user = make_user(KafkaUserWrapper)
    user._do_step({"method": "rebalance"})
    assert_failure(user, "KAFKA", "rebalance", ValueError, match="rebalance")


# ---------------------------------------------------------------------------
# LDAP
# ---------------------------------------------------------------------------

def install_fake_ldap3(monkeypatch, entries=(), search_error=None):
    state = SimpleNamespace(servers=[], connections=[])

    class FakeServer:
        def __init__(self, host):
            self.host = host
            state.servers.append(self)

    class FakeConnection:
        def __init__(self, server, user, password, auto_bind):
            self.server = server
            self.args = (user, password, auto_bind)
            self.entries = list(entries)
            self.calls = []
            state.connections.append(self)

        def bind(self):
            self.calls.append(("bind",))

        def search(self, search_base, search_filter, attributes):
            self.calls.append(("search", search_base, search_filter, attributes))
            if search_error is not None:
                raise search_error

        def unbind(self):
            self.calls.append(("unbind",))

    install_module(monkeypatch, "ldap3", Server=FakeServer, Connection=FakeConnection)
    return state


def test_ldap_connect_builds_server_and_connection(monkeypatch):
    state = install_fake_ldap3(monkeypatch)
    user = make_user(LdapUserWrapper)

    user._do_step({"method": "connect", "host": "ldap://dir:389", "user": "cn=admin", "password": "pw",
                   "auto_bind": False})

    assert_success(user, "LDAP", "connect", length=0)
    assert state.servers[0].host == "ldap://dir:389"
    assert state.connections[0].server is state.servers[0]
    assert state.connections[0].args == ("cn=admin", "pw", False)


def test_ldap_connect_defaults_to_class_host_and_auto_bind(monkeypatch):
    state = install_fake_ldap3(monkeypatch)
    user = make_user(LdapUserWrapper)

    user._do_step({"method": "connect"})

    assert state.servers[0].host == LdapUserWrapper.host
    assert state.connections[0].args == (None, None, True)


def test_ldap_search_bind_unbind(monkeypatch):
    state = install_fake_ldap3(monkeypatch, entries=["entry-one", "e2"])
    user = make_user(LdapUserWrapper)
    user._do_step({"method": "connect"})
    user._do_step({"method": "bind"})
    user._do_step({"method": "search", "base_dn": "dc=ex", "attributes": ["mail"], "name": "find"})
    user._do_step({"method": "unbind"})

    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "bind", "find", "unbind"]
    assert all(c["exception"] is None for c in calls)
    assert calls[2]["response_length"] == len("entry-one") + len("e2")
    assert state.connections[0].calls == [
        ("bind",),
        ("search", "dc=ex", "(objectClass=*)", ["mail"]),
        ("unbind",),
    ]
    assert user._connection is None


@pytest.mark.parametrize("method", ["bind", "search"])
def test_ldap_command_before_connect_fails(method):
    user = make_user(LdapUserWrapper)
    user._do_step({"method": method, "base_dn": "dc=ex"})
    assert_failure(user, "LDAP", method, RuntimeError, match="not connected")


def test_ldap_search_without_base_dn_and_server_error(monkeypatch):
    install_fake_ldap3(monkeypatch, search_error=ConnectionError("ldap gone"))
    user = make_user(LdapUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "search"})
    user._do_step({"method": "search", "base_dn": "dc=ex"})

    calls = events_of(user)
    assert isinstance(calls[0]["exception"], KeyError)
    assert isinstance(calls[1]["exception"], ConnectionError)


def test_ldap_unbind_without_connection_is_success():
    user = make_user(LdapUserWrapper)
    user._do_step({"method": "unbind"})
    assert_success(user, "LDAP", "unbind", length=0)


# ---------------------------------------------------------------------------
# Memcached
# ---------------------------------------------------------------------------

def install_fake_pymemcache(monkeypatch, store=None, raises=None):
    created = []

    class FakeClient(Recorder):
        def __init__(self, server):
            super().__init__(raises=raises)
            self.server = server
            self.store = dict(store or {})
            created.append(self)

        def get(self, key):
            self.calls.append(("get", (key,), {}))
            return self.store.get(key)

    install_module(monkeypatch, "pymemcache.client.base", Client=FakeClient)
    return created


def test_memcached_connect_set_get_delete_close(monkeypatch):
    created = install_fake_pymemcache(monkeypatch, store={"k": b"stored"})
    user = make_user(MemcachedUserWrapper)
    steps = [
        {"method": "connect", "host": "cache", "port": "11212"},
        {"method": "set", "key": "k", "value": "hello"},
        {"method": "set", "key": "b", "value": b"\x00\x01"},
        {"method": "get", "key": "k"},
        {"method": "get", "key": "missing", "name": "miss"},
        {"method": "delete", "key": "k"},
        {"method": "close"},
    ]
    for step in steps:
        user._do_step(step)

    client = created[0]
    assert client.server == ("cache", 11212)
    assert client.calls == [
        ("set", ("k", "hello"), {}),
        ("set", ("b", b"\x00\x01"), {}),
        ("get", ("k",), {}),
        ("get", ("missing",), {}),
        ("delete", ("k",), {}),
        ("close", (), {}),
    ]
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "set", "set", "get", "miss", "delete", "close"]
    assert [c["response_length"] for c in calls] == [0, 5, 2, 6, 0, 0, 0]
    assert all(c["request_type"] == "MEMCACHED" and c["exception"] is None for c in calls)
    assert user._client is None


def test_memcached_connect_defaults(monkeypatch):
    created = install_fake_pymemcache(monkeypatch)
    user = make_user(MemcachedUserWrapper)
    user._do_step({"method": "connect"})
    assert created[0].server == (MemcachedUserWrapper.host, 11211)


def test_memcached_resolves_placeholders_in_step(monkeypatch):
    created = install_fake_pymemcache(monkeypatch)
    parameter_resolver.register_variable("tb_key", "session-9")
    user = make_user(MemcachedUserWrapper)
    user._do_step({"method": "connect"})

    user._do_step({"method": "set", "key": "${var.tb_key}", "value": "v"})

    assert created[0].calls == [("set", ("session-9", "v"), {})]


@pytest.mark.parametrize("method", ["set", "get", "delete"])
def test_memcached_command_before_connect_fails(method):
    user = make_user(MemcachedUserWrapper)
    user._do_step({"method": method, "key": "k"})
    assert_failure(user, "MEMCACHED", method, RuntimeError, match="not connected")


def test_memcached_client_error_is_reported(monkeypatch):
    install_fake_pymemcache(monkeypatch, raises={"set": ConnectionResetError("reset")})
    user = make_user(MemcachedUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "set", "key": "k", "value": "v", "name": "write"})

    assert_failure(user, "MEMCACHED", "write", ConnectionResetError)


# ---------------------------------------------------------------------------
# Modbus
# ---------------------------------------------------------------------------

class FakeModbusResponse:
    def __init__(self, registers=(), error=False):
        self.registers = list(registers)
        self._error = error

    def isError(self):
        return self._error

    def __str__(self):
        return "Modbus exception response"


def install_fake_pymodbus(monkeypatch, connect_ok=True, read=None, write=None):
    created = []

    class FakeTcpClient:
        def __init__(self, host, port):
            self.host = host
            self.port = port
            self.calls = []
            self.closed = False
            created.append(self)

        def connect(self):
            return connect_ok

        def read_holding_registers(self, address, count, **_unit):
            self.calls.append(("read", address, count))
            return read or FakeModbusResponse([1, 2, 3])

        def write_register(self, address, value, **_unit):
            self.calls.append(("write", address, value))
            return write or FakeModbusResponse()

        def close(self):
            self.closed = True

    install_module(monkeypatch, "pymodbus.client", ModbusTcpClient=FakeTcpClient)
    return created


def test_modbus_connect_read_write_close(monkeypatch):
    created = install_fake_pymodbus(monkeypatch)
    user = make_user(ModbusUserWrapper)
    steps = [
        {"method": "connect", "host": "plc", "port": "5020"},
        {"method": "read_holding", "address": "4", "count": "3"},
        {"method": "write_register", "address": 5, "value": "1234", "name": "set-point"},
        {"method": "close"},
    ]
    for step in steps:
        user._do_step(step)

    client = created[0]
    assert (client.host, client.port) == ("plc", 5020)
    assert client.calls == [("read", 4, 3), ("write", 5, 1234)]
    assert client.closed is True
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "read_holding", "set-point", "close"]
    assert [c["response_length"] for c in calls] == [0, 6, 2, 0]
    assert all(c["request_type"] == "MODBUS" and c["exception"] is None for c in calls)
    assert user._client is None


def test_modbus_connect_refused_is_reported(monkeypatch):
    install_fake_pymodbus(monkeypatch, connect_ok=False)
    user = make_user(ModbusUserWrapper)
    user._do_step({"method": "connect"})
    assert_failure(user, "MODBUS", "connect", RuntimeError, match="connect failed")


@pytest.mark.parametrize("method", ["read_holding", "write_register"])
def test_modbus_error_response_is_reported(monkeypatch, method):
    bad = FakeModbusResponse(error=True)
    install_fake_pymodbus(monkeypatch, read=bad, write=bad)
    user = make_user(ModbusUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": method})

    assert_failure(user, "MODBUS", method, RuntimeError, match="Modbus exception response")


@pytest.mark.parametrize("method", ["read_holding", "write_register"])
def test_modbus_command_before_connect_fails(method):
    user = make_user(ModbusUserWrapper)
    user._do_step({"method": method})
    assert_failure(user, "MODBUS", method, RuntimeError, match="not connected")


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------

class FakeCursor(list):
    def limit(self, count):
        self.limited_to = count
        return self


class FakeCollection:
    def __init__(self, path, rows):
        self.path = path
        self.rows = rows
        self.calls = []

    def _record(self, *args):
        self.calls.append(args)

    def find_one(self, flt):
        self._record("find_one", flt)
        return self.rows[0] if self.rows else None

    def find(self, flt):
        self._record("find", flt)
        return FakeCursor(self.rows)

    def insert_one(self, document):
        self._record("insert_one", document)
        return SimpleNamespace(inserted_id=1)

    def update_one(self, flt, update):
        self._record("update_one", flt, update)
        return SimpleNamespace(modified_count=1)

    def delete_one(self, flt):
        self._record("delete_one", flt)
        return SimpleNamespace(deleted_count=1)

    def count_documents(self, flt):
        self._record("count", flt)
        return len(self.rows)


def install_fake_pymongo(monkeypatch, rows=(), error=None):
    state = SimpleNamespace(clients=[], collections={})

    class FakeMongoClient:
        def __init__(self, uri, serverSelectionTimeoutMS):
            self.uri = uri
            self.timeout = serverSelectionTimeoutMS
            state.clients.append(self)

        def __getitem__(self, database):
            if error is not None:
                raise error
            return _Database(database)

    class _Database:
        def __init__(self, name):
            self.name = name

        def __getitem__(self, collection):
            key = (self.name, collection)
            if key not in state.collections:
                state.collections[key] = FakeCollection(key, list(rows))
            return state.collections[key]

    install_module(monkeypatch, "pymongo", MongoClient=FakeMongoClient)
    return state


def test_mongo_client_uses_proxy_connection(monkeypatch):
    state = install_fake_pymongo(monkeypatch, rows=[{"a": 1}])
    proxy = fresh_proxy(monkeypatch, "mongo_user")
    proxy.connection = {"uri": "mongodb://db:27018", "timeout_ms": "250"}
    user = make_user(MongoUserWrapper)

    user._do_step({"method": "find_one", "database": "shop", "collection": "users",
                   "filter": {"email": "u@x"}, "name": "lookup"})
    user._do_step({"method": "count"})

    assert len(state.clients) == 1
    assert (state.clients[0].uri, state.clients[0].timeout) == ("mongodb://db:27018", 250)
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["lookup", "count"]
    assert all(c["request_type"] == "MONGO" and c["exception"] is None for c in calls)
    assert state.collections[("shop", "users")].calls == [("find_one", {"email": "u@x"})]
    assert state.collections[("test", "default")].calls == [("count", {})]


def test_mongo_client_defaults_to_class_host(monkeypatch):
    state = install_fake_pymongo(monkeypatch)
    fresh_proxy(monkeypatch, "mongo_user")
    user = make_user(MongoUserWrapper)

    user._do_step({"method": "find_one"})

    assert (state.clients[0].uri, state.clients[0].timeout) == (MongoUserWrapper.host, 5000)


def test_mongo_write_methods_and_lengths(monkeypatch):
    state = install_fake_pymongo(monkeypatch, rows=[{"a": 1}, {"a": 2}, {"a": 3}])
    fresh_proxy(monkeypatch, "mongo_user")
    user = make_user(MongoUserWrapper)
    steps = [
        {"method": "find", "collection": "c", "filter": {"a": {"$gt": 0}}, "limit": "2"},
        {"method": "insert_one", "collection": "c", "document": {"k": "v"}},
        {"method": "update_one", "collection": "c", "filter": {"_id": 1}, "update": {"$set": {"v": 2}}},
        {"method": "delete_one", "collection": "c", "filter": {"_id": 1}},
        {"method": "count", "collection": "c"},
    ]
    for step in steps:
        user._do_step(step)

    assert state.collections[("test", "c")].calls == [
        ("find", {"a": {"$gt": 0}}),
        ("insert_one", {"k": "v"}),
        ("update_one", {"_id": 1}, {"$set": {"v": 2}}),
        ("delete_one", {"_id": 1}),
        ("count", {}),
    ]
    calls = events_of(user)
    assert all(c["exception"] is None for c in calls)
    assert [c["response_length"] for c in calls] == [3, 1, 1, 1, 3]


def test_mongo_expect_min_passes_and_fails(monkeypatch):
    install_fake_pymongo(monkeypatch, rows=[{"a": 1}, {"a": 2}])
    fresh_proxy(monkeypatch, "mongo_user")
    user = make_user(MongoUserWrapper)

    user._do_step({"method": "count", "expect_min": 2})
    user._do_step({"method": "count", "expect_min": "3", "name": "too-few"})

    ok, failed = events_of(user)
    assert ok["exception"] is None and ok["response_length"] == 2
    assert failed["name"] == "too-few"
    assert isinstance(failed["exception"], AssertionError)
    assert ">= 3" in str(failed["exception"])
    assert failed["response_length"] == 0


def test_mongo_driver_error_is_reported(monkeypatch):
    install_fake_pymongo(monkeypatch, error=TimeoutError("server selection"))
    fresh_proxy(monkeypatch, "mongo_user")
    user = make_user(MongoUserWrapper)

    user._do_step({"method": "insert_one", "document": {}})

    assert_failure(user, "MONGO", "insert_one", TimeoutError, match="server selection")


# ---------------------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------------------

def install_fake_paho(monkeypatch, publish_rc=0, subscribe_rc=0, connect_error=None):
    created = []

    class FakeInfo:
        def __init__(self):
            self.rc = publish_rc
            self.waited = []

        def wait_for_publish(self, timeout):
            self.waited.append(timeout)

    class FakeClient:
        def __init__(self, client_id, clean_session):
            self.client_id = client_id
            self.clean_session = clean_session
            self.calls = []
            self.infos = []
            created.append(self)

        def username_pw_set(self, username, password):
            self.calls.append(("auth", username, password))

        def connect(self, host, port, keepalive):
            if connect_error is not None:
                raise connect_error
            self.calls.append(("connect", host, port, keepalive))

        def loop_start(self):
            self.calls.append(("loop_start",))

        def loop_stop(self):
            self.calls.append(("loop_stop",))

        def disconnect(self):
            self.calls.append(("disconnect",))

        def publish(self, topic, payload, qos, retain):
            self.calls.append(("publish", topic, payload, qos, retain))
            info = FakeInfo()
            self.infos.append(info)
            return info

        def subscribe(self, topic, qos):
            self.calls.append(("subscribe", topic, qos))
            return subscribe_rc, 1

    install_module(monkeypatch, "paho.mqtt.client", Client=FakeClient)
    return created


def test_mqtt_publish_connects_once_and_publishes(monkeypatch):
    created = install_fake_paho(monkeypatch)
    user = make_user(MqttUserWrapper)

    user._do_step({"broker": "mq:1884", "topic": "t/x", "payload": "hello", "qos": "1", "retain": True,
                   "username": "u", "password": "p", "client_id": "cid", "keepalive": 30, "timeout": 2})
    user._do_step({"method": "publish", "broker": "mq:1884", "topic": "t/y", "payload": b"\x01"})

    assert len(created) == 1
    client = created[0]
    assert (client.client_id, client.clean_session) == ("cid", True)
    assert client.calls[:3] == [("auth", "u", "p"), ("connect", "mq", 1884, 30), ("loop_start",)]
    assert client.calls[3:] == [("publish", "t/x", "hello", 1, True), ("publish", "t/y", b"\x01", 0, False)]
    assert client.infos[0].waited == [2.0]
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["publish:t/x", "publish:t/y"]
    assert [c["url"] for c in calls] == ["mq:1884", "mq:1884"]
    assert [c["response_length"] for c in calls] == [5, 1]
    assert all(c["request_type"] == "MQTT" and c["exception"] is None for c in calls)


def test_mqtt_connect_defaults_and_generated_client_id(monkeypatch):
    created = install_fake_paho(monkeypatch)
    user = make_user(MqttUserWrapper)

    user._do_step({"method": "connect", "name": "open"})

    assert_success(user, "MQTT", "open", length=0)
    client = created[0]
    assert client.client_id.startswith("loaddensity-")
    assert client.calls == [("connect", "127.0.0.1", 1883, 60), ("loop_start",)]


def test_mqtt_switching_broker_disconnects_previous_client(monkeypatch):
    created = install_fake_paho(monkeypatch)
    user = make_user(MqttUserWrapper)

    user._do_step({"method": "connect", "broker": "a:1"})
    user._do_step({"method": "connect", "broker": "b:2"})

    assert len(created) == 2
    assert created[0].calls[-1] == ("disconnect",)
    assert created[1].calls[0] == ("connect", "b", 2, 60)
    assert user._client is created[1]


def test_mqtt_subscribe_success_and_failure(monkeypatch):
    install_fake_paho(monkeypatch, subscribe_rc=0)
    user = make_user(MqttUserWrapper)
    user._do_step({"method": "subscribe", "topic": "t", "qos": 2})
    assert_success(user, "MQTT", "subscribe:t", length=0)
    assert user._client.calls[-1] == ("subscribe", "t", 2)

    install_fake_paho(monkeypatch, subscribe_rc=128)
    other = make_user(MqttUserWrapper)
    other._do_step({"method": "subscribe", "topic": "t"})
    assert_failure(other, "MQTT", "subscribe:t", RuntimeError, match="rc=128")


def test_mqtt_publish_bad_rc_is_reported(monkeypatch):
    install_fake_paho(monkeypatch, publish_rc=4)
    user = make_user(MqttUserWrapper)
    user._do_step({"method": "publish", "topic": "t", "payload": "x"})
    assert_failure(user, "MQTT", "publish:t", RuntimeError, match="rc=4")


def test_mqtt_connect_error_is_reported(monkeypatch):
    install_fake_paho(monkeypatch, connect_error=ConnectionRefusedError("refused"))
    user = make_user(MqttUserWrapper)
    user._do_step({"method": "connect"})
    assert_failure(user, "MQTT", "connect:", ConnectionRefusedError)
    assert user._client is None


def test_mqtt_disconnect_tears_down_client(monkeypatch):
    created = install_fake_paho(monkeypatch)
    user = make_user(MqttUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "disconnect"})

    assert_success(user, "MQTT", "disconnect:", length=0)
    assert created[0].calls[-2:] == [("loop_stop",), ("disconnect",)]
    assert user._client is None


def test_mqtt_unknown_method_fires_value_error(monkeypatch):
    install_fake_paho(monkeypatch)
    user = make_user(MqttUserWrapper)
    user._do_step({"method": "retain_all", "topic": "t"})
    assert_failure(user, "MQTT", "retain_all:t", ValueError, match="retain_all")


def test_mqtt_on_stop_cleans_up(monkeypatch):
    created = install_fake_paho(monkeypatch)
    user = make_user(MqttUserWrapper)
    user._do_step({"method": "connect"})

    user.on_stop()

    assert created[0].calls[-2:] == [("loop_stop",), ("disconnect",)]
    assert user._client is None


# ---------------------------------------------------------------------------
# NATS
# ---------------------------------------------------------------------------

def install_fake_nats(monkeypatch, messages=(), next_error=None):
    state = SimpleNamespace(clients=[], subs=[])

    class FakeSub:
        def __init__(self, subject):
            self.subject = subject
            self.pending = list(messages)
            self.timeouts = []
            self.unsubscribed = False

        async def next_msg(self, timeout):
            self.timeouts.append(timeout)
            if next_error is not None:
                raise next_error
            return SimpleNamespace(data=self.pending.pop(0))

        async def unsubscribe(self):
            self.unsubscribed = True

    class FakeNatsClient:
        def __init__(self, servers):
            self.servers = servers
            self.published = []
            self.requests = []
            self.closed = False

        async def publish(self, subject, payload):
            self.published.append((subject, payload))

        async def subscribe(self, subject):
            sub = FakeSub(subject)
            state.subs.append(sub)
            return sub

        async def request(self, subject, payload, timeout):
            self.requests.append((subject, payload, timeout))
            return SimpleNamespace(data=b"pong!")

        async def close(self):
            self.closed = True

    async def connect(servers):
        client = FakeNatsClient(servers)
        state.clients.append(client)
        return client

    install_module(monkeypatch, "nats", connect=connect)
    return state


def test_nats_connect_publish_request_close(monkeypatch):
    state = install_fake_nats(monkeypatch)
    user = make_user(NatsUserWrapper)
    steps = [
        {"method": "connect", "servers": ["nats://a:4222", "nats://b:4222"]},
        {"method": "publish", "subject": "orders", "payload": "héllo"},
        {"method": "publish", "subject": "orders", "payload": 42, "name": "num"},
        {"method": "request", "subject": "rpc", "payload": b"ping", "timeout": "0.5"},
        {"method": "close"},
    ]
    for step in steps:
        user._do_step(step)

    client = state.clients[0]
    assert client.servers == ["nats://a:4222", "nats://b:4222"]
    assert client.published == [("orders", "héllo".encode("utf-8")), ("orders", b"42")]
    assert client.requests == [("rpc", b"ping", 0.5)]
    assert client.closed is True
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "publish", "num", "request", "close"]
    assert [c["response_length"] for c in calls] == [0, len("héllo".encode("utf-8")), 2, 5, 0]
    assert all(c["request_type"] == "NATS" and c["exception"] is None for c in calls)
    assert user._client is None


def test_nats_connect_falls_back_to_url_then_host(monkeypatch):
    state = install_fake_nats(monkeypatch)
    user = make_user(NatsUserWrapper)

    user._do_step({"method": "connect", "url": "nats://x:1"})
    user._do_step({"method": "connect"})

    assert [c.servers for c in state.clients] == [["nats://x:1"], [NatsUserWrapper.host]]


def test_nats_subscribe_collects_messages_and_unsubscribes(monkeypatch):
    state = install_fake_nats(monkeypatch, messages=[b"ab", b"cde"])
    user = make_user(NatsUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "subscribe", "subject": "s", "max_messages": "2", "timeout": 0.25})

    assert_success(user, "NATS", "subscribe", length=5)
    sub = state.subs[0]
    assert sub.subject == "s"
    assert sub.timeouts == [0.25, 0.25]
    assert sub.unsubscribed is True


def test_nats_subscribe_timeout_still_unsubscribes(monkeypatch):
    state = install_fake_nats(monkeypatch, next_error=TimeoutError("no message"))
    user = make_user(NatsUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "subscribe", "subject": "s"})

    assert_failure(user, "NATS", "subscribe", TimeoutError, match="no message")
    assert state.subs[0].unsubscribed is True


def test_nats_close_without_client_is_success():
    user = make_user(NatsUserWrapper)
    user._do_step({"method": "close"})
    assert_success(user, "NATS", "close", length=0)


# ---------------------------------------------------------------------------
# Neo4j
# ---------------------------------------------------------------------------

def install_fake_neo4j(monkeypatch, records=(), run_error=None):
    state = SimpleNamespace(drivers=[])

    class FakeSession:
        def __init__(self, driver, database):
            self.driver = driver
            self.database = database

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.driver.sessions_closed += 1
            return False

        def run(self, cypher, parameters):
            self.driver.runs.append((self.database, cypher, parameters))
            if run_error is not None:
                raise run_error
            return iter(records)

    class FakeDriver:
        def __init__(self, uri, auth):
            self.uri = uri
            self.auth = auth
            self.runs = []
            self.sessions_closed = 0
            self.closed = False

        def session(self, database):
            return FakeSession(self, database)

        def close(self):
            self.closed = True

    class FakeGraphDatabase:
        @staticmethod
        def driver(uri, auth):
            driver = FakeDriver(uri, auth)
            state.drivers.append(driver)
            return driver

    install_module(monkeypatch, "neo4j", GraphDatabase=FakeGraphDatabase)
    return state


def test_neo4j_connect_run_close(monkeypatch):
    state = install_fake_neo4j(monkeypatch, records=["<Record n=1>", "<Record n=22>"])
    user = make_user(Neo4jUserWrapper)
    steps = [
        {"method": "connect", "uri": "bolt://g:7687", "user": "admin", "password": "pw"},
        {"method": "RUN", "cypher": "MATCH (n) RETURN n", "parameters": {"x": 1}, "database": "movies",
         "name": "match-all"},
        {"method": "close"},
    ]
    for step in steps:
        user._do_step(step)

    driver = state.drivers[0]
    assert (driver.uri, driver.auth) == ("bolt://g:7687", ("admin", "pw"))
    assert driver.runs == [("movies", "MATCH (n) RETURN n", {"x": 1})]
    assert driver.sessions_closed == 1
    assert driver.closed is True
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "match-all", "close"]
    assert calls[1]["response_length"] == len("<Record n=1>") + len("<Record n=22>")
    assert all(c["request_type"] == "NEO4J" and c["exception"] is None for c in calls)
    assert user._driver is None


def test_neo4j_connect_defaults(monkeypatch):
    state = install_fake_neo4j(monkeypatch)
    user = make_user(Neo4jUserWrapper)
    user._do_step({"method": "connect"})
    user._do_step({"method": "run", "cypher": "RETURN 1"})
    driver = state.drivers[0]
    assert (driver.uri, driver.auth) == (Neo4jUserWrapper.host, ("neo4j", "neo4j"))
    assert driver.runs == [(None, "RETURN 1", {})]


def test_neo4j_run_before_connect_and_query_error(monkeypatch):
    user = make_user(Neo4jUserWrapper)
    user._do_step({"method": "run", "cypher": "RETURN 1"})
    assert_failure(user, "NEO4J", "run", RuntimeError, match="not connected")

    install_fake_neo4j(monkeypatch, run_error=ValueError("syntax error"))
    other = make_user(Neo4jUserWrapper)
    other._do_step({"method": "connect"})
    events_of(other).clear()
    other._do_step({"method": "run", "cypher": "BAD"})
    assert_failure(other, "NEO4J", "run", ValueError, match="syntax error")


def test_neo4j_close_without_driver_is_success():
    user = make_user(Neo4jUserWrapper)
    user._do_step({"method": "close"})
    assert_success(user, "NEO4J", "close", length=0)


# ---------------------------------------------------------------------------
# OPC-UA
# ---------------------------------------------------------------------------

def install_fake_asyncua(monkeypatch, value=3.25, children=("a", "b", "c"), read_error=None):
    state = SimpleNamespace(clients=[])

    class FakeNode:
        def __init__(self, client, node_id):
            self.client = client
            self.node_id = node_id

        async def read_value(self):
            if read_error is not None:
                raise read_error
            return value

        async def write_value(self, new_value):
            self.client.writes.append((self.node_id, new_value))

        async def get_children(self):
            return list(children)

    class FakeClient:
        def __init__(self, url):
            self.url = url
            self.connected = False
            self.nodes = []
            self.writes = []
            state.clients.append(self)

        async def connect(self):
            self.connected = True

        def get_node(self, node_id):
            self.nodes.append(node_id)
            return FakeNode(self, node_id)

        async def disconnect(self):
            self.connected = False

    install_module(monkeypatch, "asyncua", Client=FakeClient)
    return state


def test_opcua_connect_read_write_browse_disconnect(monkeypatch):
    state = install_fake_asyncua(monkeypatch)
    user = make_user(OpcuaUserWrapper)
    steps = [
        {"method": "connect", "url": "opc.tcp://plc:4840"},
        {"method": "read", "node_id": "ns=2;i=2"},
        {"method": "write", "node_id": "ns=2;i=3", "value": 42, "name": "set"},
        {"method": "browse"},
        {"method": "disconnect"},
    ]
    for step in steps:
        user._do_step(step)

    client = state.clients[0]
    assert client.url == "opc.tcp://plc:4840"
    assert client.nodes == ["ns=2;i=2", "ns=2;i=3", "i=85"]
    assert client.writes == [("ns=2;i=3", 42)]
    assert client.connected is False
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "read", "set", "browse", "disconnect"]
    assert [c["response_length"] for c in calls] == [0, len("3.25"), 2, 3, 0]
    assert all(c["request_type"] == "OPC-UA" and c["exception"] is None for c in calls)
    assert user._client is None


def test_opcua_connect_defaults_to_class_host(monkeypatch):
    state = install_fake_asyncua(monkeypatch)
    user = make_user(OpcuaUserWrapper)
    user._do_step({"method": "connect"})
    assert state.clients[0].url == OpcuaUserWrapper.host
    assert state.clients[0].connected is True


@pytest.mark.parametrize("method", ["read", "write", "browse"])
def test_opcua_command_before_connect_fails(method):
    user = make_user(OpcuaUserWrapper)
    user._do_step({"method": method, "node_id": "i=1", "value": 1})
    assert_failure(user, "OPC-UA", method, RuntimeError, match="not connected")


def test_opcua_read_error_is_reported(monkeypatch):
    install_fake_asyncua(monkeypatch, read_error=TimeoutError("bad node"))
    user = make_user(OpcuaUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "read", "node_id": "ns=9;i=9"})

    assert_failure(user, "OPC-UA", "read", TimeoutError, match="bad node")


def test_opcua_disconnect_without_client_is_success():
    user = make_user(OpcuaUserWrapper)
    user._do_step({"method": "disconnect"})
    assert_success(user, "OPC-UA", "disconnect", length=0)


# ---------------------------------------------------------------------------
# Pulsar
# ---------------------------------------------------------------------------

def install_fake_pulsar(monkeypatch, messages=(b"m1", b"msg2"), receive_error=None):
    state = SimpleNamespace(clients=[])

    class FakeProducer:
        def __init__(self, topic):
            self.topic = topic
            self.sent = []
            self.closed = False

        def send(self, payload):
            self.sent.append(payload)

        def close(self):
            self.closed = True

    class FakeConsumer:
        def __init__(self, topic, subscription):
            self.topic = topic
            self.subscription = subscription
            self.pending = [SimpleNamespace(data=lambda body=body: body) for body in messages]
            self.timeouts = []
            self.acked = []
            self.closed = False

        def receive(self, timeout_millis):
            self.timeouts.append(timeout_millis)
            if receive_error is not None:
                raise receive_error
            return self.pending.pop(0)

        def acknowledge(self, message):
            self.acked.append(message.data())

        def close(self):
            self.closed = True

    class FakeClient:
        def __init__(self, url):
            self.url = url
            self.producers = []
            self.consumers = []
            self.closed = False
            state.clients.append(self)

        def create_producer(self, topic):
            producer = FakeProducer(topic)
            self.producers.append(producer)
            return producer

        def subscribe(self, topic, subscription):
            consumer = FakeConsumer(topic, subscription)
            self.consumers.append(consumer)
            return consumer

        def close(self):
            self.closed = True

    install_module(monkeypatch, "pulsar", Client=FakeClient)
    return state


def test_pulsar_produce_reuses_producer_per_topic(monkeypatch):
    state = install_fake_pulsar(monkeypatch)
    user = make_user(PulsarUserWrapper)
    user._do_step({"method": "connect", "url": "pulsar://p:6650"})
    user._do_step({"method": "produce", "topic": "t", "payload": "hello"})
    user._do_step({"method": "produce", "topic": "t", "payload": 7, "name": "num"})
    user._do_step({"method": "produce", "topic": "u", "payload": b"\x00"})

    client = state.clients[0]
    assert client.url == "pulsar://p:6650"
    assert [p.topic for p in client.producers] == ["t", "u"]
    assert client.producers[0].sent == [b"hello", b"7"]
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "produce", "num", "produce"]
    assert [c["response_length"] for c in calls] == [0, 5, 1, 1]
    assert all(c["request_type"] == "PULSAR" and c["exception"] is None for c in calls)


def test_pulsar_consume_receives_and_acknowledges(monkeypatch):
    state = install_fake_pulsar(monkeypatch)
    user = make_user(PulsarUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "consume", "topic": "t", "subscription": "s", "max_messages": 2, "timeout_ms": "250"})

    assert_success(user, "PULSAR", "consume", length=len(b"m1") + len(b"msg2"))
    client = state.clients[0]
    assert client.url == PulsarUserWrapper.host
    consumer = client.consumers[0]
    assert (consumer.topic, consumer.subscription) == ("t", "s")
    assert consumer.timeouts == [250, 250]
    assert consumer.acked == [b"m1", b"msg2"]


def test_pulsar_consume_default_subscription_and_receive_error(monkeypatch):
    state = install_fake_pulsar(monkeypatch, receive_error=TimeoutError("pulsar timeout"))
    user = make_user(PulsarUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "consume", "topic": "t"})

    assert_failure(user, "PULSAR", "consume", TimeoutError, match="pulsar timeout")
    consumer = state.clients[0].consumers[0]
    assert consumer.subscription == "default"
    assert consumer.timeouts == [1000]


def test_pulsar_close_releases_everything(monkeypatch):
    state = install_fake_pulsar(monkeypatch)
    user = make_user(PulsarUserWrapper)
    user._do_step({"method": "connect"})
    user._do_step({"method": "produce", "topic": "t"})
    user._do_step({"method": "consume", "topic": "t"})
    events_of(user).clear()

    user._do_step({"method": "close"})

    assert_success(user, "PULSAR", "close", length=0)
    client = state.clients[0]
    assert client.closed is True
    assert client.producers[0].closed is True
    assert client.consumers[0].closed is True
    assert user._client is None and user._producers == {} and user._consumers == {}


@pytest.mark.parametrize("method", ["produce", "consume"])
def test_pulsar_command_before_connect_fails(method):
    user = make_user(PulsarUserWrapper)
    user._do_step({"method": method, "topic": "t"})
    assert_failure(user, "PULSAR", method, RuntimeError, match="not connected")


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

class FakeRedis:
    def __init__(self, data=None, error=None):
        self.data = dict(data or {})
        self.lists = {}
        self.calls = []
        self.error = error

    def _hit(self, *call):
        self.calls.append(call)
        if self.error is not None:
            raise self.error

    def get(self, key):
        self._hit("get", key)
        return self.data.get(key)

    def set(self, key, value):
        self._hit("set", key, value)
        self.data[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    def incr(self, key):
        self._hit("incr", key)
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    def lpush(self, key, value):
        self._hit("lpush", key, value)
        self.lists.setdefault(key, []).insert(0, value.encode("utf-8"))
        return len(self.lists[key])

    def rpop(self, key):
        self._hit("rpop", key)
        items = self.lists.get(key) or []
        return items.pop() if items else None

    def delete(self, key):
        self._hit("delete", key)
        return 1 if self.data.pop(key, None) is not None else 0

    def exists(self, key):
        self._hit("exists", key)
        return 1 if key in self.data else 0


def redis_user_with(client):
    user = make_user(RedisUserWrapper)
    user._client = client
    return user


def test_redis_command_dispatch_and_lengths():
    client = FakeRedis()
    user = redis_user_with(client)
    steps = [
        {"method": "set", "key": "k", "value": "hello"},
        {"method": "get", "key": "k", "expect": "hello"},
        {"method": "incr", "key": "n"},
        {"method": "lpush", "key": "q", "value": "x"},
        {"method": "rpop", "key": "q", "name": "pop"},
        {"method": "rpop", "key": "q", "name": "pop-empty"},
        {"method": "exists", "key": "k"},
        {"method": "delete", "key": "k"},
    ]
    for step in steps:
        user._do_step(step)

    assert [c[0] for c in client.calls] == ["set", "get", "incr", "lpush", "rpop", "rpop", "exists", "delete"]
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["set", "get", "incr", "lpush", "pop", "pop-empty", "exists", "delete"]
    assert [c["response_length"] for c in calls] == [1, 5, 1, 1, 1, 0, 1, 1]
    assert all(c["request_type"] == "REDIS" and c["exception"] is None for c in calls)


def test_redis_expect_mismatch_fails():
    user = redis_user_with(FakeRedis({"k": b"actual"}))
    user._do_step({"method": "get", "key": "k", "expect": "wanted"})
    event = assert_failure(user, "REDIS", "get", AssertionError, match="'wanted'")
    assert "'actual'" in str(event["exception"])


def test_redis_expect_against_missing_key_and_int_result():
    user = redis_user_with(FakeRedis({"n": 4}))
    user._do_step({"method": "get", "key": "absent", "expect": "x"})
    user._do_step({"method": "incr", "key": "n", "expect": 5})

    missing, incremented = events_of(user)
    assert isinstance(missing["exception"], AssertionError)
    assert "''" in str(missing["exception"])
    assert incremented["exception"] is None


def test_redis_client_error_is_reported():
    user = redis_user_with(FakeRedis(error=ConnectionError("redis down")))
    user._do_step({"method": "get", "key": "k"})
    assert_failure(user, "REDIS", "get", ConnectionError, match="redis down")


def test_redis_unknown_method_fires_no_event():
    client = FakeRedis()
    user = redis_user_with(client)
    user._do_step({"method": "flushall"})
    assert events_of(user) == []
    assert client.calls == []


def test_redis_client_built_from_proxy_url_then_host(monkeypatch):
    urls = []

    class FakeRedisModule:
        @staticmethod
        def from_url(url):
            urls.append(url)
            return FakeRedis()

    install_module(monkeypatch, "redis", Redis=FakeRedisModule)
    proxy = fresh_proxy(monkeypatch, "redis_user")
    proxy.connection = {"url": "redis://cache:6380/2"}
    first = make_user(RedisUserWrapper)
    first._do_step({"method": "get", "key": "k"})
    first._do_step({"method": "get", "key": "k"})

    proxy.connection = None
    second = make_user(RedisUserWrapper)
    second._do_step({"method": "get", "key": "k"})

    assert urls == ["redis://cache:6380/2", RedisUserWrapper.host]
    assert len(events_of(first)) == 2


def test_redis_missing_library_raises_clear_runtime_error(monkeypatch):
    block_module(monkeypatch, "redis")
    user = make_user(RedisUserWrapper)
    with pytest.raises(RuntimeError, match="redis is required") as info:
        user._ensure_client()
    assert isinstance(info.value.__cause__, ImportError)


# ---------------------------------------------------------------------------
# SFTP
# ---------------------------------------------------------------------------

def install_fake_paramiko(monkeypatch, listing=("a.txt", "bb.log"), download_bytes=b"downloaded", put_error=None):
    state = SimpleNamespace(transports=[], clients=[])

    class FakeTransport:
        def __init__(self, address):
            self.address = address
            self.connect_kwargs = None
            self.closed = False
            state.transports.append(self)

        def connect(self, **kwargs):
            self.connect_kwargs = kwargs

        def close(self):
            self.closed = True

    class FakeSftp:
        def __init__(self, transport):
            self.transport = transport
            self.calls = []
            self.closed = False

        def listdir(self, path):
            self.calls.append(("listdir", path))
            return list(listing)

        def put(self, local, remote):
            self.calls.append(("put", local, remote))
            if put_error is not None:
                raise put_error

        def get(self, remote, local):
            self.calls.append(("get", remote, local))
            with open(local, "wb") as handle:
                handle.write(download_bytes)

        def close(self):
            self.closed = True

    class FakeSFTPClient:
        @staticmethod
        def from_transport(transport):
            client = FakeSftp(transport)
            state.clients.append(client)
            return client

    install_module(monkeypatch, "paramiko", Transport=FakeTransport, SFTPClient=FakeSFTPClient)
    return state


def test_sftp_connect_list_disconnect(monkeypatch):
    state = install_fake_paramiko(monkeypatch)
    user = make_user(SftpUserWrapper)
    user._do_step({"method": "connect", "host": "files", "port": "2222", "username": "u", "password": "p"})
    user._do_step({"method": "list", "path": "/data"})
    user._do_step({"method": "disconnect"})

    transport = state.transports[0]
    assert transport.address == ("files", 2222)
    assert transport.connect_kwargs == {"username": "u", "password": "p", "pkey": None}
    client = state.clients[0]
    assert client.transport is transport
    assert client.calls == [("listdir", "/data")]
    assert client.closed is True and transport.closed is True
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["connect", "list", "disconnect"]
    assert [c["response_length"] for c in calls] == [0, len("a.txt") + len("bb.log"), 0]
    assert all(c["request_type"] == "SFTP" and c["exception"] is None for c in calls)
    assert user._sftp is None and user._transport is None


def test_sftp_connect_defaults(monkeypatch):
    state = install_fake_paramiko(monkeypatch)
    user = make_user(SftpUserWrapper)
    user._do_step({"method": "connect"})
    assert state.transports[0].address == ("127.0.0.1", 22)
    assert state.transports[0].connect_kwargs == {"username": "", "password": None, "pkey": None}


def test_sftp_upload_and_download_report_file_sizes(monkeypatch, tmp_path):
    state = install_fake_paramiko(monkeypatch, download_bytes=b"0123456789ab")
    local = tmp_path / "payload.bin"
    local.write_bytes(b"x" * 17)
    target = tmp_path / "fetched.bin"
    user = make_user(SftpUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "upload", "local": str(local), "remote": "/srv/in.bin"})
    user._do_step({"method": "upload", "local": str(local), "name": "upload-default-remote"})
    user._do_step({"method": "download", "remote": "/srv/out.bin", "local": str(target)})

    assert state.clients[0].calls == [
        ("put", str(local), "/srv/in.bin"),
        ("put", str(local), "payload.bin"),
        ("get", "/srv/out.bin", str(target)),
    ]
    calls = events_of(user)
    assert [c["name"] for c in calls] == ["upload", "upload-default-remote", "download"]
    assert [c["response_length"] for c in calls] == [17, 17, 12]
    assert all(c["exception"] is None for c in calls)


def test_sftp_transfer_error_is_reported(monkeypatch, tmp_path):
    install_fake_paramiko(monkeypatch, put_error=PermissionError("denied"))
    local = tmp_path / "f.txt"
    local.write_text("data", encoding="utf-8")
    user = make_user(SftpUserWrapper)
    user._do_step({"method": "connect"})
    events_of(user).clear()

    user._do_step({"method": "upload", "local": str(local)})

    assert_failure(user, "SFTP", "upload", PermissionError, match="denied")


@pytest.mark.parametrize("method", ["list", "upload", "download"])
def test_sftp_command_before_connect_fails(method):
    user = make_user(SftpUserWrapper)
    user._do_step({"method": method, "local": "x", "remote": "y"})
    assert_failure(user, "SFTP", method, RuntimeError, match="not connected")


def test_sftp_disconnect_without_connection_is_success():
    user = make_user(SftpUserWrapper)
    user._do_step({"method": "disconnect"})
    assert_success(user, "SFTP", "disconnect", length=0)


def test_imap_lengths_are_the_payload_sizes(monkeypatch):
    install_fake_imap(monkeypatch)
    user = make_user(ImapUserWrapper)
    for method in ("connect", "search", "fetch"):
        user._do_step({"method": method})
    assert [event["response_length"] for event in events_of(user)] == [len(b"noop"), len(b"1 2"), len(b"x")]


def test_imap_non_ok_status_is_a_failure():
    user = make_user(ImapUserWrapper)
    user._client = Recorder(returns={"select": ("NO", [b"no such mailbox"])})
    user._do_step({"method": "select", "mailbox": "Gone"})
    assert_failure(user, "IMAP", "select", RuntimeError, match="NO")


class _Pymodbus35Client:
    """Signatures of pymodbus 3.5: the unit is ``slave``."""

    def __init__(self):
        self.units = []

    def read_holding_registers(self, address, count, slave=0, **kwargs):
        self.units.append(("slave", slave))
        return FakeModbusResponse([1])

    def write_register(self, address, value, slave=0, **kwargs):
        self.units.append(("slave", slave))
        return FakeModbusResponse()


class _Pymodbus315Client:
    """Signatures of pymodbus 3.15: the unit is ``device_id`` and ``slave`` is rejected."""

    def __init__(self):
        self.units = []

    def read_holding_registers(self, address, count, device_id=1, no_response_expected=False):
        self.units.append(("device_id", device_id))
        return FakeModbusResponse([1])

    def write_register(self, address, value, device_id=1, no_response_expected=False):
        self.units.append(("device_id", device_id))
        return FakeModbusResponse()


@pytest.mark.parametrize("client_cls, keyword", [(_Pymodbus35Client, "slave"), (_Pymodbus315Client, "device_id")])
def test_modbus_unit_uses_the_keyword_of_the_installed_pymodbus(client_cls, keyword):
    user = make_user(ModbusUserWrapper)
    user._client = client_cls()
    user._do_step({"method": "read_holding", "unit": 7})
    user._do_step({"method": "write_register", "value": 1, "unit": 7})
    assert user._client.units == [(keyword, 7), (keyword, 7)]
    assert all(event["exception"] is None for event in events_of(user))
