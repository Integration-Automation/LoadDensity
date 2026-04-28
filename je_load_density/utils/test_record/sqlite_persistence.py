import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance

_SCHEMA = """
CREATE TABLE IF NOT EXISTS load_density_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    label TEXT,
    metadata_json TEXT
);
CREATE TABLE IF NOT EXISTS load_density_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    method TEXT,
    test_url TEXT,
    name TEXT,
    status_code TEXT,
    response_time_ms REAL,
    response_length INTEGER,
    error TEXT,
    FOREIGN KEY (run_id) REFERENCES load_density_runs(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_records_run_id ON load_density_records(run_id);
CREATE INDEX IF NOT EXISTS idx_records_name ON load_density_records(name);
"""

_lock = threading.Lock()


def _connect(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    with connection:
        connection.executescript(_SCHEMA)


def persist_records(
    database_path: str,
    label: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    將目前的測試紀錄寫入 SQLite。
    Persist the current test records into SQLite. Returns the run id.
    """
    started_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

    with _lock:
        connection = _connect(database_path)
        try:
            _ensure_schema(connection)
            with connection:
                cursor = connection.execute(
                    "INSERT INTO load_density_runs (started_at, label, metadata_json) VALUES (?, ?, ?)",
                    (started_at, label, metadata_json),
                )
                run_id = int(cursor.lastrowid)

                rows: List[tuple] = []
                for record in test_record_instance.test_record_list:
                    rows.append(_to_row(run_id, "success", record))
                for record in test_record_instance.error_record_list:
                    rows.append(_to_row(run_id, "failure", record))

                if rows:
                    connection.executemany(
                        "INSERT INTO load_density_records "
                        "(run_id, outcome, method, test_url, name, status_code, "
                        " response_time_ms, response_length, error) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        rows,
                    )
            return run_id
        finally:
            connection.close()


def _to_row(run_id: int, outcome: str, record: Dict[str, Any]) -> tuple:
    return (
        run_id,
        outcome,
        record.get("Method"),
        record.get("test_url"),
        record.get("name"),
        record.get("status_code"),
        record.get("response_time_ms"),
        record.get("response_length"),
        record.get("error"),
    )


def list_runs(database_path: str, limit: int = 20) -> List[Dict[str, Any]]:
    connection = _connect(database_path)
    try:
        _ensure_schema(connection)
        cursor = connection.execute(
            "SELECT id, started_at, label, metadata_json FROM load_density_runs "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


def fetch_run_records(database_path: str, run_id: int) -> Iterable[Dict[str, Any]]:
    connection = _connect(database_path)
    try:
        _ensure_schema(connection)
        cursor = connection.execute(
            "SELECT outcome, method, test_url, name, status_code, "
            "       response_time_ms, response_length, error "
            "FROM load_density_records WHERE run_id = ?",
            (run_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()
