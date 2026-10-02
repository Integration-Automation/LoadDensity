import sqlite3

import pytest

pytest.importorskip("je_action_core.request_context", reason="coordinated ActionCore request-record release")

from je_action_core.request_record import RequestRecordError

from je_load_density.utils.test_record.run_context import RunContext
from je_load_density.utils.test_record.sqlite_persistence import (
    fetch_canonical_records,
    fetch_run_records,
    persist_canonical_records,
    persist_records,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance


def context():
    return RunContext(source="loaddensity", phase="load", engine="asyncio")


def capture(run, **changes):
    fields = {"protocol": "http", "request_method": "GET", "request_url": "http://localhost/",
              "name": "health", "status_code": 200, "start_time": 100, "end_time": 100.025,
              "response_time_ms": 25, "response_length": 2, "outcome": "passed", "error": None,
              "extensions": {"label": "測試", "nested": [True, 1]}}
    return run.capture({**fields, **changes})


def test_round_trip_multiple_runs_and_empty_run(tmp_path):
    database = str(tmp_path / "records.sqlite")
    first, second, empty = context(), context(), context()
    first_record = capture(first)
    second_record = capture(second, status_code=201)
    for run in [first, second, empty]:
        assert persist_canonical_records(database, run) == run.run_id
    assert fetch_canonical_records(database, first.run_id) == [first_record]
    assert fetch_canonical_records(database, second.run_id) == [second_record]
    assert fetch_canonical_records(database, empty.run_id) == []


def test_existing_legacy_database_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(test_record_instance, "test_record_list", [
        {"Method": "GET", "test_url": "http://legacy/", "status_code": "200", "response_time_ms": 12}
    ])
    monkeypatch.setattr(test_record_instance, "error_record_list", [])
    database = str(tmp_path / "records.sqlite")
    legacy_id = persist_records(database)
    before = list(fetch_run_records(database, legacy_id))
    assert before[0]["test_url"] == "http://legacy/"
    run = context()
    capture(run)
    persist_canonical_records(database, run)
    assert list(fetch_run_records(database, legacy_id)) == before
    assert len(fetch_canonical_records(database, run.run_id)) == 1


def test_retry_is_idempotent_and_conflict_rolls_back_batch(tmp_path, monkeypatch):
    database = str(tmp_path / "records.sqlite")
    run = context()
    original = capture(run)
    persist_canonical_records(database, run)
    persist_canonical_records(database, run)
    fresh = capture(run, status_code=201)
    conflicting = {**original, "extensions": {"label": "測試", "nested": [1, 1]}}
    monkeypatch.setattr(run, "snapshot", lambda: [fresh, conflicting])
    with pytest.raises(RequestRecordError, match="record_id"):
        persist_canonical_records(database, run)
    assert fetch_canonical_records(database, run.run_id) == [original]


def test_invalid_or_foreign_snapshot_rejected_before_writes(tmp_path, monkeypatch):
    database = str(tmp_path / "records.sqlite")
    run = context()
    original = capture(run)
    persist_canonical_records(database, run)
    fresh = capture(run, status_code=201)
    monkeypatch.setattr(run, "snapshot", lambda: [fresh, {**original, "schema_version": 2}])
    with pytest.raises(RequestRecordError, match="schema_version"):
        persist_canonical_records(database, run)
    foreign = capture(context())
    monkeypatch.setattr(run, "snapshot", lambda: [foreign])
    with pytest.raises(RequestRecordError, match="run_id"):
        persist_canonical_records(database, run)
    assert fetch_canonical_records(database, run.run_id) == [original]


def test_corrupted_database_record_is_not_returned_as_valid(tmp_path):
    database = str(tmp_path / "records.sqlite")
    run = context()
    capture(run)
    persist_canonical_records(database, run)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE request_records_v1 SET record_json = ?", ('{"schema_version": 2}',))
    with pytest.raises(RequestRecordError):
        fetch_canonical_records(database, run.run_id)
