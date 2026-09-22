"""
Smoke tests for the expansion modules.

Covers fuzz, OWASP checks, error clustering, FSM, cookie jars, the
action formatter, action generator, stub server, and notifiers (with
mocked posters). External-dep modules (HTTP/3, AMQP, NATS, etc.) are
asserted only on import + lazy-error surface.
"""

import io
import json
import sqlite3
import urllib.request
from contextlib import closing

import pytest


def test_fuzz_mutate_string_returns_variants():
    from je_load_density.utils.security.fuzz import mutate_string

    variants = mutate_string("seed", count=3)
    assert len(variants) == 3
    assert variants[0] == "seed"


def test_fuzz_mutate_json_changes_one_key():
    from je_load_density.utils.security.fuzz import mutate_json

    variants = mutate_json({"a": 1, "b": 2}, count=5)
    assert len(variants) == 5
    assert all(isinstance(v, dict) for v in variants)


def test_owasp_check_security_headers_flags_all_missing():
    from je_load_density.utils.security.owasp_checks import check_security_headers

    findings = check_security_headers({})
    rule_set = {f["rule"] for f in findings}
    assert "owasp.api8.missing_hsts" in rule_set
    assert "owasp.api8.missing_csp" in rule_set


def test_owasp_check_security_headers_passes_when_present():
    from je_load_density.utils.security.owasp_checks import check_security_headers

    findings = check_security_headers({
        "Strict-Transport-Security": "max-age=63072000",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'self'",
    })
    assert findings == []


def test_error_clustering_collapses_dynamic_tokens():
    from je_load_density.utils.regression.error_clustering import cluster_errors

    clusters = cluster_errors([
        {"error": "timeout after 0xdeadbeef"},
        {"error": "timeout after 0xfeedface"},
        {"error": "invalid id 42"},
    ])
    counts = {c["signature"]: c["count"] for c in clusters}
    assert any("<hex>" in sig for sig in counts)


def test_fsm_runner_walks_states():
    from je_load_density.utils.scenario.fsm import FsmRunner

    tasks = [
        {"state": "login", "transitions": {"success": "browse"}},
        {"state": "browse", "transitions": {"success": "logout"}},
        {"state": "logout", "transitions": {}},
    ]
    runner = FsmRunner(tasks)
    history = runner.run(lambda _: "success", max_steps=10)
    assert [h["state"] for h in history] == ["login", "browse", "logout"]


def test_cookie_jar_isolated_per_user():
    from je_load_density.utils.scenario.cookie_jar import (
        jar_for_user, reset_user_jar,
    )

    jar1 = jar_for_user(1)
    jar2 = jar_for_user(2)
    assert jar1 is not jar2
    reset_user_jar(1)


def test_action_formatter_sorts_task_keys():
    from je_load_density.utils.linter.action_formatter import format_action_document

    doc = {"load_density": [["LD_start_test", {"tasks": [{
        "json": {"x": 1}, "method": "post", "request_url": "/x", "name": "n",
    }]}]]}
    formatted = format_action_document(doc)
    task = formatted["load_density"][0][1]["tasks"][0]
    keys = list(task.keys())
    assert keys[0] == "method"
    assert "request_url" in keys[:3]


def test_action_generator_merges_docs():
    from je_load_density.utils.action_generator.generate import merge_actions

    merged = merge_actions(
        {"load_density": [["A"]]},
        {"load_density": [["B"]]},
    )
    assert merged == {"load_density": [["A"], ["B"]]}


def test_multi_run_trend_handles_empty_database(tmp_path):
    from je_load_density.utils.regression.multi_run_trend import trend_runs

    db_path = tmp_path / "empty.db"
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.executescript(
            "CREATE TABLE load_density_runs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, label TEXT, "
            "metadata_json TEXT);"
            "CREATE TABLE load_density_records ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, outcome TEXT, "
            "name TEXT, response_time_ms REAL);"
        )
    result = trend_runs(str(db_path), limit=5)
    assert result == {"per_run": [], "per_name": {}}


def test_pagerduty_payload_shape():
    from je_load_density.utils.notifier.pagerduty import build_pagerduty_event

    payload = build_pagerduty_event(
        "rk", {"totals": {"requests": 1, "failures": 0, "failure_rate": 0},
               "latency_overall": {"p95_ms": 1.0}},
    )
    assert payload["routing_key"] == "rk"
    assert payload["event_action"] == "trigger"


def test_opsgenie_payload_shape():
    from je_load_density.utils.notifier.opsgenie import build_opsgenie_alert

    payload = build_opsgenie_alert(
        {"totals": {"requests": 1, "failures": 0, "failure_rate": 0},
         "latency_overall": {"p95_ms": 1.0}},
    )
    assert payload["alias"] == "loaddensity-sla"
    assert payload["priority"] == "P3"


def test_gitlab_note_markdown():
    from je_load_density.utils.notifier.gitlab import build_gitlab_mr_note

    text = build_gitlab_mr_note(
        {"totals": {"requests": 10, "failures": 1, "failure_rate": 0.1},
         "latency_overall": {"p95_ms": 200.0}},
    )
    assert "requests" in text
    assert "200" in text


def test_stub_server_serves_rule(tmp_path):
    from je_load_density.utils.stub_server.stub_server import (
        start_stub_server, stop_stub_server,
    )

    info = start_stub_server(
        rules=[{"method": "GET", "path_regex": r"^/x$",
                "status": 200, "json": {"ok": True}}],
        host="127.0.0.1", port=0,
    )
    try:
        with urllib.request.urlopen(
            f"http://{info['host']}:{info['port']}/x", timeout=2.0,
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
            assert body == {"ok": True}
    finally:
        stop_stub_server()


def test_action_yaml_round_trip(tmp_path):
    try:
        from je_load_density.utils.json.json_file.yaml_file import (
            read_action_yaml, write_action_yaml,
        )
    except ImportError:
        pytest.skip("pyyaml not installed")
    path = tmp_path / "actions.yaml"
    doc = {"load_density": [["LD_clear_records"]]}
    try:
        write_action_yaml(str(path), doc)
        loaded = read_action_yaml(str(path))
    except RuntimeError as error:
        pytest.skip(f"pyyaml not installed: {error}")
    assert loaded == doc


def test_action_toml_round_trip(tmp_path):
    from je_load_density.utils.json.json_file.toml_file import (
        read_action_toml, write_action_toml,
    )
    path = tmp_path / "actions.toml"
    doc = {"label": "smoke", "enabled": True, "users": 50}
    write_action_toml(str(path), doc)
    loaded = read_action_toml(str(path))
    assert loaded["label"] == "smoke"
    assert loaded["users"] == 50


def test_executor_has_new_commands():
    from je_load_density.utils.executor.action_executor import executor

    must_have = {
        "LD_generate_histogram_report",
        "LD_format_action_string",
        "LD_trend_runs",
        "LD_cluster_errors",
        "LD_post_pagerduty_event",
        "LD_start_stub_server",
        "LD_mutate_string",
        "LD_run_owasp_checks",
        "LD_toxiproxy_install_latency",
        "LD_chaos_network_delay",
    }
    missing = must_have - set(executor.event_dict)
    assert missing == set(), f"missing: {missing}"


def test_user_registry_has_new_users():
    from je_load_density.wrapper.start_wrapper.start_test import _USER_REGISTRY

    must_have = {
        "http3_user", "graphql_ws_user", "amqp_user", "nats_user", "pulsar_user",
        "coap_user", "cassandra_user", "elasticsearch_user",
        "smtp_user", "imap_user", "ftp_user", "sftp_user", "fuzz_http_user",
    }
    missing = must_have - set(_USER_REGISTRY)
    assert missing == set(), f"missing: {missing}"


def test_toxiproxy_module_imports():
    from je_load_density.utils.chaos.toxiproxy import (
        create_proxy, install_latency,
    )
    assert callable(create_proxy)
    assert callable(install_latency)


def test_chaos_mesh_module_imports():
    from je_load_density.utils.chaos.chaos_mesh import (
        apply_manifest, build_network_delay,
    )
    assert callable(apply_manifest)
    manifest = build_network_delay(
        name="lag", namespace="default",
        selector_labels={"app": "x"}, latency="50ms", duration="10s",
    )
    assert manifest["kind"] == "NetworkChaos"
