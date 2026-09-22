"""
Smoke tests for the second expansion sprint.

Covers JWT attacks, GraphQL/SSRF/smuggling/rate-limit checks, new
reports (Excel/SARIF/CycloneDX/service-map/cost), data utilities (PII,
factory, db fixtures), governance (tagging, audit, share link),
AI helpers (auto-tune, smart shape), canary verdict, asyncio engine
helpers, executor + user-registry growth, and i18n.
"""

import asyncio
import base64
import json
import sqlite3
import tempfile
import time
import zipfile
from contextlib import closing
from pathlib import Path

import pytest


# ---------- Security: JWT ---------------------------------------------------


def test_alg_none_token_has_empty_signature():
    from je_load_density.utils.security.jwt_attacks import craft_alg_none_token

    token = craft_alg_none_token({"sub": "alice"})
    parts = token.split(".")
    assert len(parts) == 3
    assert parts[2] == ""
    header = json.loads(base64.urlsafe_b64decode(parts[0] + "==="))
    assert header["alg"] == "none"


def test_jwt_attack_pack_includes_required_keys():
    from je_load_density.utils.security.jwt_attacks import craft_attack_pack

    pack = craft_attack_pack({"sub": "x"}, public_key_pem="-----BEGIN PUBLIC KEY-----")
    assert {"alg_none", "expired", "kid_traversal", "rs_to_hs_confusion"} <= set(pack)


# ---------- Security: GraphQL / SSRF / smuggling ----------------------------


def test_graphql_depth_attack_nests_correctly():
    from je_load_density.utils.security.graphql_checks import build_depth_attack

    payload = build_depth_attack(depth=5)
    assert payload["query"].count("node") >= 5


def test_ssrf_targets_include_metadata():
    from je_load_density.utils.security.ssrf_checks import (
        build_ssrf_targets, find_metadata_leak,
    )
    targets = build_ssrf_targets()
    assert any("169.254.169.254" in t for t in targets)
    assert "iam/security-credentials" in find_metadata_leak("see iam/security-credentials")[0]


def test_smuggling_pack_returns_three_variants():
    from je_load_density.utils.security.smuggling_checks import smuggling_attack_pack

    pack = smuggling_attack_pack("example.com")
    assert set(pack) == {"cl_te", "te_cl", "te_te"}
    assert all("Host: example.com" in payload for payload in pack.values())


# ---------- New reports -----------------------------------------------------


def test_excel_report_is_valid_xlsx(tmp_path):
    from je_load_density.utils.generate_report.generate_excel_report import (
        generate_excel_report,
    )

    cwd = Path.cwd()
    import os
    os.chdir(tmp_path)
    try:
        path = generate_excel_report("smoke")
    finally:
        os.chdir(cwd)
    assert zipfile.is_zipfile(path)


def test_sarif_report_has_runs(tmp_path):
    from je_load_density.utils.generate_report.generate_sarif_report import (
        generate_sarif_report,
    )

    cwd = Path.cwd()
    import os
    os.chdir(tmp_path)
    try:
        path = generate_sarif_report("smoke")
    finally:
        os.chdir(cwd)
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    assert body["version"] == "2.1.0"


def test_cyclonedx_report_lists_components(tmp_path):
    from je_load_density.utils.generate_report.generate_cyclonedx_report import (
        generate_cyclonedx_report,
    )

    cwd = Path.cwd()
    import os
    os.chdir(tmp_path)
    try:
        path = generate_cyclonedx_report("smoke")
    finally:
        os.chdir(cwd)
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    assert body["bomFormat"] == "CycloneDX"
    assert isinstance(body["components"], list)


def test_service_map_has_nodes_and_edges(tmp_path):
    from je_load_density.utils.generate_report.generate_service_map import (
        generate_service_map,
    )

    cwd = Path.cwd()
    import os
    os.chdir(tmp_path)
    try:
        path = generate_service_map("smoke")
    finally:
        os.chdir(cwd)
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    assert "nodes" in body and "edges" in body


def test_cost_estimate_math():
    from je_load_density.utils.generate_report.generate_cost_report import (
        estimate_run_cost,
    )

    breakdown = estimate_run_cost(
        duration_seconds=3600, workers=2, hourly_rate_usd=0.1, egress_gb=1.0,
    )
    assert breakdown["compute_usd"] == 0.2  # 2 workers * 1h * 0.1
    assert breakdown["egress_usd"] == 0.09


# ---------- Data / state ----------------------------------------------------


def test_pii_anonymizer_scrubs_email_phone():
    from je_load_density.utils.data.pii_anonymizer import scrub_string

    text = scrub_string("alice@example.com phoned +1 555 123 4567")
    assert "alice@example.com" not in text
    assert "+1 555 123 4567" not in text


def test_factory_builds_pool():
    from je_load_density.utils.data.factory import build_user_pool

    pool = build_user_pool(3)
    assert len(pool) == 3
    assert len({user["email"] for user in pool}) == 3


# ---------- Governance ------------------------------------------------------


def test_run_tagging_round_trip(tmp_path):
    from je_load_density.utils.governance.run_tagging import (
        list_tags, search_runs_by_tag, tag_run,
    )

    db_path = tmp_path / "runs.db"
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.executescript(
            "CREATE TABLE load_density_runs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, label TEXT, "
            "metadata_json TEXT);"
        )
        connection.execute(
            "INSERT INTO load_density_runs (started_at, label, metadata_json) "
            "VALUES ('t', 'l', '{}')"
        )
        connection.commit()
        run_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]

    tag_run(str(db_path), run_id, {"env": "staging", "branch": "dev"})
    tags = list_tags(str(db_path), run_id)
    assert tags == {"env": "staging", "branch": "dev"}
    hits = search_runs_by_tag(str(db_path), "env", "staging")
    assert any(row["id"] == run_id for row in hits)


def test_audit_log_appends(tmp_path):
    from je_load_density.utils.governance.audit_log import (
        append_audit_entry, read_audit_log,
    )

    log_path = tmp_path / "audit.jsonl"
    append_audit_entry(str(log_path), "run", user="alice", details={"action": "smoke"})
    entries = read_audit_log(str(log_path))
    assert len(entries) == 1
    assert entries[0]["action"] == "run"


def test_share_link_round_trip():
    from je_load_density.utils.governance.share_link import (
        issue_share_link, verify_share_link,
    )

    secret = "topsecret"
    url = issue_share_link("https://reports.example", "/r/123.html", secret,
                            expires_in_seconds=300)
    token = url.split("token=", 1)[1]
    payload = verify_share_link(token, secret)
    assert payload["p"] == "/r/123.html"


def test_share_link_rejects_bad_signature():
    from je_load_density.utils.governance.share_link import (
        issue_share_link, verify_share_link,
    )

    url = issue_share_link("https://reports.example", "/r/123.html", "secret",
                            expires_in_seconds=300)
    token = url.split("token=", 1)[1]
    with pytest.raises(ValueError):
        verify_share_link(token, "different-secret")


# ---------- AI ---------------------------------------------------------------


def test_auto_tuner_increases_users_when_latency_under_target():
    from je_load_density.utils.ai.auto_tune import AutoTuner

    tuner = AutoTuner(target_p95_ms=500.0, initial_users=10, gain=1.0)
    step = tuner.next_step(measured_p95_ms=100.0)
    assert step["users"] > 10


def test_smart_shape_finds_safe_users():
    from je_load_density.utils.ai.smart_shape import find_breaking_point

    result = find_breaking_point(
        probe=lambda users: 0.0 if users <= 50 else 0.5,
        min_users=1, max_users=100, failure_threshold=0.05,
    )
    assert result["safe_users"] <= 50
    assert result["safe_users"] >= 1


def test_root_cause_prompt_includes_summary():
    from je_load_density.utils.ai.root_cause import build_root_cause_prompt

    context = build_root_cause_prompt(
        diff_report={"has_regressions": True},
        error_clusters=[{"signature": "timeout", "count": 5}],
        summary={"totals": {"requests": 1000}},
        include_git_log=False,
    )
    assert "task" in context
    assert context["summary"]["totals"]["requests"] == 1000


# ---------- Canary ----------------------------------------------------------


def test_canary_verdict_rolls_back_on_regression():
    from je_load_density.utils.ci_annotations.canary_analysis import canary_verdict

    baseline = {"totals": {"failure_rate": 0.0},
                "latency_overall": {"p50_ms": 50, "p95_ms": 200, "p99_ms": 400}}
    candidate = {"totals": {"failure_rate": 0.05},
                  "latency_overall": {"p50_ms": 60, "p95_ms": 800, "p99_ms": 1500}}
    verdict = canary_verdict(baseline, candidate, sla_rules=[])
    assert verdict["verdict"] == "rollback"
    assert verdict["reasons"]


def test_canary_verdict_promotes_when_steady():
    from je_load_density.utils.ci_annotations.canary_analysis import canary_verdict

    baseline = {"totals": {"failure_rate": 0.01},
                "latency_overall": {"p50_ms": 50, "p95_ms": 200, "p99_ms": 400}}
    candidate = {"totals": {"failure_rate": 0.01},
                  "latency_overall": {"p50_ms": 52, "p95_ms": 210, "p99_ms": 420}}
    verdict = canary_verdict(baseline, candidate, sla_rules=[])
    assert verdict["verdict"] == "promote"


# ---------- Asyncio engine + bench CLI --------------------------------------


def test_asyncio_engine_returns_summary():
    """
    Verify the engine wiring — httpx invocation, error-record path, and
    summary-dict return shape. Uses a non-routable port so every attempt
    fails fast; we're asserting plumbing, not network behaviour.
    """
    from je_load_density.engine.asyncio_engine import run_async_load
    from je_load_density.utils.test_record.test_record_class import test_record_instance

    test_record_instance.clear_records()
    try:
        result = asyncio.run(run_async_load(
            tasks=[{"method": "get",
                    "request_url": "http://127.0.0.1:1/never",
                    "timeout": 0.2}],
            users=1, duration_seconds=0.6,
        ))
    except RuntimeError as error:
        pytest.skip(f"httpx not installed: {error}")
    assert "requests" in result and "failures" in result
    assert result["failures"] >= 1


# ---------- DX --------------------------------------------------------------


def test_i18n_translates_known_key():
    from je_load_density.utils.dx.i18n import t, available_locales

    assert t("missing_locust", "zh-TW") != t("missing_locust", "en")
    assert "zh-TW" in available_locales()


def test_profile_call_returns_text():
    from je_load_density.utils.dx.profiler import profile_call

    result, text = profile_call(sum, [1, 2, 3])
    assert result == 6
    assert "function calls" in text


# ---------- Executor + registry growth --------------------------------------


def test_executor_has_wave2_commands():
    from je_load_density.utils.executor.action_executor import executor

    must_have = {
        "LD_generate_excel_report", "LD_generate_sarif_report",
        "LD_generate_cyclonedx_report", "LD_generate_service_map",
        "LD_generate_cost_report",
        "LD_craft_alg_none_token", "LD_craft_jwt_attack_pack",
        "LD_graphql_attack_pack", "LD_ssrf_targets", "LD_smuggling_attack_pack",
        "LD_probe_rate_limit",
        "LD_pii_scrub", "LD_build_user_pool",
        "LD_tag_run", "LD_append_audit_entry",
        "LD_issue_share_link", "LD_verify_share_link",
        "LD_build_root_cause_prompt", "LD_find_breaking_point",
        "LD_calibrate_sla", "LD_canary_verdict",
        "LD_cdp_capture_to_har",
    }
    missing = must_have - set(executor.event_dict)
    assert missing == set(), f"missing: {missing}"


def test_user_registry_has_wave2_users():
    from je_load_density.wrapper.start_wrapper.start_test import _USER_REGISTRY

    must_have = {
        "soap_user", "ldap_user", "snmp_user", "modbus_user", "opcua_user",
        "zmq_user", "thrift_user",
        "memcached_user", "neo4j_user", "couchbase_user",
        "etcd_user", "consul_user", "vault_user",
        "webpush_user", "apns_user", "fcm_user",
    }
    missing = must_have - set(_USER_REGISTRY)
    assert missing == set(), f"missing: {missing}"
