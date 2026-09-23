"""
A ``connection`` dict given to a template's ``set_wrapper_*`` setter supplies default step fields.

Covers the templates that dispatch a step through ``_command_for`` (amqp, elasticsearch, ftp,
graphql_ws, imap, ldap, modbus, nats, opcua, pulsar, sftp) or through a module-level sender
(coap, http3, fuzz_http). The step each template hands on is captured, so no client library runs.
A value named in the step always wins.
"""

import importlib
from types import SimpleNamespace

import pytest

from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy

TEMPLATE_PACKAGE = "je_load_density.wrapper.user_template"

# template module name -> (proxy key, user class, setter)
COMMAND_TEMPLATES = {
    "amqp": ("amqp_user", "AmqpUserWrapper", "set_wrapper_amqp_user"),
    "elasticsearch": ("elasticsearch_user", "ElasticsearchUserWrapper", "set_wrapper_elasticsearch_user"),
    "ftp": ("ftp_user", "FtpUserWrapper", "set_wrapper_ftp_user"),
    "graphql_ws": ("graphql_ws_user", "GraphQLWebSocketUserWrapper", "set_wrapper_graphql_ws_user"),
    "imap": ("imap_user", "ImapUserWrapper", "set_wrapper_imap_user"),
    "ldap": ("ldap_user", "LdapUserWrapper", "set_wrapper_ldap_user"),
    "modbus": ("modbus_user", "ModbusUserWrapper", "set_wrapper_modbus_user"),
    "nats": ("nats_user", "NatsUserWrapper", "set_wrapper_nats_user"),
    "opcua": ("opcua_user", "OpcuaUserWrapper", "set_wrapper_opcua_user"),
    "pulsar": ("pulsar_user", "PulsarUserWrapper", "set_wrapper_pulsar_user"),
    "sftp": ("sftp_user", "SftpUserWrapper", "set_wrapper_sftp_user"),
}

# template module name -> (proxy key, user class, setter, module-level sender to replace)
SENDER_TEMPLATES = {
    "coap": ("coap_user", "CoapUserWrapper", "set_wrapper_coap_user", "_send_coap"),
    "http3": ("http3_user", "Http3UserWrapper", "set_wrapper_http3_user", "_send_h3_request"),
}

CONNECTION = {"marker": "from-setter", "timeout": 7}


@pytest.fixture(autouse=True)
def isolated_resolver(monkeypatch):
    monkeypatch.setattr(parameter_resolver, "_variables", {})
    monkeypatch.setattr(parameter_resolver, "_csv_sources", {})


def load(name):
    # name is a key of COMMAND_TEMPLATES / SENDER_TEMPLATES or "fuzz_http", never outside input.
    return importlib.import_module(f"{TEMPLATE_PACKAGE}.{name}_user_template")  # nosemgrep


def configure(monkeypatch, module, key, setter_name):
    """Give ``key`` a fresh proxy for the test, then configure it through the public setter."""
    fresh = type(locust_wrapper_proxy.user_dict[key])()
    monkeypatch.setitem(locust_wrapper_proxy.user_dict, key, fresh)
    getattr(module, setter_name)({}, tasks=[], connection=dict(CONNECTION))


def make_user(module, class_name):
    env = SimpleNamespace(events=SimpleNamespace(request=SimpleNamespace(fire=lambda **_: None)))
    return getattr(module, class_name)(env)


def step_through_command(monkeypatch, name, raw_step):
    key, class_name, setter_name = COMMAND_TEMPLATES[name]
    module = load(name)
    configure(monkeypatch, module, key, setter_name)
    user = make_user(module, class_name)
    seen = []

    def handler(step):
        seen.append(step)
        return 0

    user._command_for = lambda _method: handler
    user._do_step(raw_step)
    return seen


def step_through_sender(monkeypatch, name, raw_step):
    key, class_name, setter_name, sender = SENDER_TEMPLATES[name]
    module = load(name)
    configure(monkeypatch, module, key, setter_name)
    seen = []

    async def fake_send(step):
        seen.append(step)
        return 200, 0

    monkeypatch.setattr(module, sender, fake_send)
    make_user(module, class_name)._do_step(raw_step)
    return seen


@pytest.mark.parametrize("name", sorted(COMMAND_TEMPLATES))
def test_command_template_uses_setter_connection_as_step_defaults(monkeypatch, name):
    seen = step_through_command(monkeypatch, name, {"method": "connect"})
    assert len(seen) == 1  # nosec B101
    assert seen[0]["marker"] == "from-setter"  # nosec B101
    assert seen[0]["timeout"] == 7  # nosec B101


@pytest.mark.parametrize("name", sorted(COMMAND_TEMPLATES))
def test_command_template_step_fields_override_setter_connection(monkeypatch, name):
    seen = step_through_command(monkeypatch, name, {"method": "connect", "marker": "from-step"})
    assert seen[0]["marker"] == "from-step"  # nosec B101
    assert seen[0]["timeout"] == 7  # nosec B101


@pytest.mark.parametrize("name", sorted(SENDER_TEMPLATES))
def test_sender_template_uses_setter_connection_as_step_defaults(monkeypatch, name):
    seen = step_through_sender(monkeypatch, name, {"name": "probe"})
    assert len(seen) == 1  # nosec B101
    assert seen[0]["marker"] == "from-setter"  # nosec B101
    assert seen[0]["timeout"] == 7  # nosec B101


@pytest.mark.parametrize("name", sorted(SENDER_TEMPLATES))
def test_sender_template_step_fields_override_setter_connection(monkeypatch, name):
    seen = step_through_sender(monkeypatch, name, {"name": "probe", "marker": "from-step"})
    assert seen[0]["marker"] == "from-step"  # nosec B101
    assert seen[0]["timeout"] == 7  # nosec B101


def fuzz_seed(monkeypatch, raw_step):
    module = load("fuzz_http")
    configure(monkeypatch, module, "fuzz_http_user", "set_wrapper_fuzz_http_user")
    seeds = []

    def fake_expand(seed, _count):
        seeds.append(seed)
        return []

    monkeypatch.setattr(module, "expand_task_fuzz", fake_expand)
    make_user(module, "FuzzHttpUserWrapper")._do_step(raw_step)
    return seeds


def test_fuzz_http_uses_setter_connection_as_seed_defaults(monkeypatch):
    seeds = fuzz_seed(monkeypatch, {"request_url": "https://svc.example/"})
    assert seeds[0]["marker"] == "from-setter"  # nosec B101
    assert seeds[0]["request_url"] == "https://svc.example/"  # nosec B101


def test_fuzz_http_seed_fields_override_setter_connection(monkeypatch):
    seeds = fuzz_seed(monkeypatch, {"request_url": "https://svc.example/", "marker": "from-step"})
    assert seeds[0]["marker"] == "from-step"  # nosec B101
