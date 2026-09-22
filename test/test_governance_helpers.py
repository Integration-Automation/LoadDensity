"""Real tests for the ``utils/governance`` helpers: the JSONL audit log, SQLite run tagging, signed share
links and the action-JSON test catalog.

Every file and database lives under ``tmp_path``; the clock is moved with ``monkeypatch`` to exercise
link expiry.
"""
import json
import re
import sqlite3

import pytest

from je_load_density.utils.governance import audit_log, run_tagging, share_link, test_catalog
from je_load_density.utils.test_record.sqlite_persistence import _SCHEMA

# --- audit_log -------------------------------------------------------------------------------------


def test_append_and_read_audit_entries(tmp_path):
    log = tmp_path / "audit.jsonl"
    audit_log.append_audit_entry(str(log), "start_test", user="alice", details={"users": 10})
    audit_log.append_audit_entry(str(log), "stop_test", user="bob")
    entries = audit_log.read_audit_log(str(log))
    assert [(row["user"], row["action"]) for row in entries] == [("alice", "start_test"), ("bob", "stop_test")]
    assert entries[0]["details"] == {"users": 10}
    assert entries[1]["details"] == {}
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", entries[0]["timestamp"])


def test_audit_user_comes_from_env_then_anonymous(tmp_path, monkeypatch):
    log = str(tmp_path / "audit.jsonl")
    monkeypatch.setenv("LD_AUDIT_USER", "ci-bot")
    audit_log.append_audit_entry(log, "a")
    monkeypatch.delenv("LD_AUDIT_USER")
    audit_log.append_audit_entry(log, "b")
    assert [row["user"] for row in audit_log.read_audit_log(log)] == ["ci-bot", "anonymous"]


def test_audit_entries_keep_non_ascii_text_unescaped(tmp_path):
    log = tmp_path / "audit.jsonl"
    audit_log.append_audit_entry(str(log), "標記", user="陳")
    raw = log.read_text(encoding="utf-8")
    assert "標記" in raw and "陳" in raw
    assert raw.endswith("\n")


def test_read_audit_log_missing_file_returns_empty(tmp_path):
    assert audit_log.read_audit_log(str(tmp_path / "missing.jsonl")) == []


def test_read_audit_log_skips_blank_and_corrupt_lines(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text('{"action": "a"}\n\n   \nnot json\n{"action": "b"}\n', encoding="utf-8")
    assert [row["action"] for row in audit_log.read_audit_log(str(log))] == ["a", "b"]


# --- run_tagging -----------------------------------------------------------------------------------

@pytest.fixture()
def runs_db(tmp_path):
    path = tmp_path / "runs.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(_SCHEMA)
    for index in range(1, 4):
        connection.execute(
            "INSERT INTO load_density_runs (started_at, label) VALUES (?, ?)", (f"t{index}", f"run{index}"),
        )
    connection.commit()
    connection.close()
    return str(path)


def test_list_tags_on_fresh_database_creates_schema(tmp_path):
    assert run_tagging.list_tags(str(tmp_path / "new.sqlite"), 1) == {}


def test_tag_run_stores_stringified_values(runs_db):
    run_tagging.tag_run(runs_db, 1, {"owner": "qa", "build": 42})
    assert run_tagging.list_tags(runs_db, 1) == {"owner": "qa", "build": "42"}
    assert run_tagging.list_tags(runs_db, 2) == {}


def test_tag_run_overwrites_existing_key(runs_db):
    run_tagging.tag_run(runs_db, 1, {"env": "staging"})
    run_tagging.tag_run(runs_db, 1, {"env": "prod"})
    assert run_tagging.list_tags(runs_db, 1) == {"env": "prod"}


def test_search_runs_by_tag_returns_matching_runs_newest_first(runs_db):
    run_tagging.tag_run(runs_db, 1, {"branch": "main"})
    run_tagging.tag_run(runs_db, 3, {"branch": "main"})
    run_tagging.tag_run(runs_db, 2, {"branch": "dev"})
    rows = run_tagging.search_runs_by_tag(runs_db, "branch", "main")
    assert rows == [
        {"id": 3, "started_at": "t3", "label": "run3"},
        {"id": 1, "started_at": "t1", "label": "run1"},
    ]


def test_search_runs_by_tag_compares_value_as_string(runs_db):
    run_tagging.tag_run(runs_db, 2, {"ticket": 7})
    assert [row["id"] for row in run_tagging.search_runs_by_tag(runs_db, "ticket", 7)] == [2]
    assert run_tagging.search_runs_by_tag(runs_db, "ticket", "8") == []


# --- share_link ------------------------------------------------------------------------------------

def _token(url):
    return url.split("?token=", 1)[1]


def test_issue_and_verify_round_trip():
    url = share_link.issue_share_link("https://host/share/", "reports/a.html", "s3cret", extra_claims={"who": "qa"})
    assert url.startswith("https://host/share?token=")
    payload = share_link.verify_share_link(_token(url), "s3cret")
    assert payload["p"] == "reports/a.html"
    assert payload["who"] == "qa"
    assert re.fullmatch(r"[0-9a-f]{16}", payload["n"])


def test_extra_claims_cannot_override_reserved_fields():
    url = share_link.issue_share_link("u", "real.html", "k", extra_claims={"p": "evil.html", "exp": 1})
    payload = share_link.verify_share_link(_token(url), "k")
    assert payload["p"] == "real.html"
    assert payload["exp"] > 1


def test_expiry_is_at_least_sixty_seconds(monkeypatch):
    monkeypatch.setattr(share_link.time, "time", lambda: 1_000_000.0)
    url = share_link.issue_share_link("u", "r", "k", expires_in_seconds=5)
    assert share_link.verify_share_link(_token(url), "k")["exp"] == 1_000_060


def test_two_links_for_same_report_differ_by_nonce():
    first = share_link.issue_share_link("u", "r", "k")
    second = share_link.issue_share_link("u", "r", "k")
    assert first != second


def test_verify_rejects_expired_token(monkeypatch):
    monkeypatch.setattr(share_link.time, "time", lambda: 1_000_000.0)
    token = _token(share_link.issue_share_link("u", "r", "k", expires_in_seconds=60))
    monkeypatch.setattr(share_link.time, "time", lambda: 1_000_061.0)
    with pytest.raises(ValueError, match="expired"):
        share_link.verify_share_link(token, "k")


def test_verify_rejects_wrong_secret_and_tampered_body():
    token = _token(share_link.issue_share_link("u", "r", "k"))
    with pytest.raises(ValueError, match="bad signature"):
        share_link.verify_share_link(token, "other")
    body, signature = token.split(".")
    forged = share_link._b64url(json.dumps({"p": "/etc/passwd", "exp": 9_999_999_999}).encode("utf-8"))
    assert forged != body
    with pytest.raises(ValueError, match="bad signature"):
        share_link.verify_share_link(f"{forged}.{signature}", "k")


def test_verify_rejects_token_without_separator():
    with pytest.raises(ValueError, match="malformed"):
        share_link.verify_share_link("no-dot-here", "k")


# --- test_catalog ----------------------------------------------------------------------------------

def _write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


@pytest.fixture()
def catalog_dir(tmp_path):
    root = tmp_path / "actions"
    _write_json(root / "login.json", {"metadata": {
        "name": "Login flow", "owner": "alice", "tags": ["smoke", "auth"], "description": "Signs in",
    }})
    _write_json(root / "nested" / "checkout.json", {"metadata": {
        "name": "Checkout", "owner": "bob", "tags": ["regression"], "description": "Buys a smoke detector",
    }})
    _write_json(root / "bare.json", [["LD_start_test", {}]])
    _write_json(root / "broken.json", "{not json")
    _write_json(root / "notes.txt", "{}")
    return root


def _by_name(entries):
    return {entry["name"]: entry for entry in entries}


def test_index_catalog_reads_metadata_recursively(catalog_dir):
    entries = _by_name(test_catalog.index_catalog([str(catalog_dir)]))
    assert set(entries) == {"Login flow", "Checkout", "bare.json"}
    assert entries["Login flow"]["tags"] == ["smoke", "auth"]
    assert entries["Checkout"]["path"].endswith("checkout.json")


def test_index_catalog_defaults_for_docs_without_metadata(catalog_dir):
    bare = _by_name(test_catalog.index_catalog([str(catalog_dir)]))["bare.json"]
    assert bare["owner"] == "" and bare["tags"] == [] and bare["description"] == ""


def test_index_catalog_skips_missing_directories(tmp_path, catalog_dir):
    entries = test_catalog.index_catalog([str(tmp_path / "nope"), str(catalog_dir)])
    assert len(entries) == 3


def test_search_catalog_by_tag_owner_and_text(catalog_dir):
    entries = test_catalog.index_catalog([str(catalog_dir)])
    assert [row["name"] for row in test_catalog.search_catalog(entries, tag="smoke")] == ["Login flow"]
    assert [row["name"] for row in test_catalog.search_catalog(entries, owner="bob")] == ["Checkout"]
    assert {row["name"] for row in test_catalog.search_catalog(entries, text="SMOKE")} == {"Checkout"}
    assert {row["name"] for row in test_catalog.search_catalog(entries, text="login")} == {"Login flow"}


def test_search_catalog_filters_combine_and_empty_filters_return_all(catalog_dir):
    entries = test_catalog.index_catalog([str(catalog_dir)])
    assert test_catalog.search_catalog(entries, tag="smoke", owner="bob") == []
    assert test_catalog.search_catalog(entries) == entries


def test_index_catalog_reads_a_single_string_tag_as_one_tag(tmp_path):
    _write_json(tmp_path / "one.json", {"metadata": {"name": "One", "tags": "smoke"}})
    entries = test_catalog.index_catalog([str(tmp_path)])
    assert entries[0]["tags"] == ["smoke"]
    assert test_catalog.search_catalog(entries, tag="smoke") == entries


def test_index_catalog_keeps_going_past_malformed_metadata(tmp_path):
    _write_json(tmp_path / "a_bad.json", {"metadata": "not a mapping"})
    _write_json(tmp_path / "b_good.json", {"metadata": {"name": "Good"}})
    names = sorted(entry["name"] for entry in test_catalog.index_catalog([str(tmp_path)]))
    assert names == ["Good", "a_bad.json"]
