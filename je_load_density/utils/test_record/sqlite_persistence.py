import json
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance

if TYPE_CHECKING:
    from je_action_core.request_context import RunContext
    from je_action_core.request_record import RequestRecord

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


_CANONICAL_TABLES = (
    "CREATE TABLE IF NOT EXISTS request_runs_v1 (run_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL "
    "CHECK(schema_version = 1))",
    "CREATE TABLE IF NOT EXISTS request_records_v1 (sequence INTEGER PRIMARY KEY, record_id TEXT NOT NULL, "
    "run_id TEXT NOT NULL, record_json TEXT NOT NULL, UNIQUE(run_id, record_id), "
    "FOREIGN KEY(run_id) REFERENCES request_runs_v1(run_id))",
    "CREATE INDEX IF NOT EXISTS idx_request_records_v1_run ON request_records_v1(run_id)",
)


def _canonical_rows(context: "RunContext") -> list[tuple[str, str, str]]:
    from je_action_core.request_record import RequestRecordError, validate_request_record

    rows = []
    for record in context.snapshot():
        validated = validate_request_record(record)
        if validated["run_id"] != context.run_id:
            raise RequestRecordError("run_id: snapshot contains a foreign run")
        payload = json.dumps(validated, ensure_ascii=False, allow_nan=False, sort_keys=True)
        rows.append((validated["record_id"], context.run_id, payload))
    return rows


def _ensure_canonical_schema(connection: sqlite3.Connection) -> None:
    for statement in _CANONICAL_TABLES:
        connection.execute(statement)


def _insert_canonical_row(connection: sqlite3.Connection, row: tuple[str, str, str]) -> None:
    from je_action_core.request_record import RequestRecordError

    previous = connection.execute(
        "SELECT record_json FROM request_records_v1 WHERE run_id = ? AND record_id = ?", (row[1], row[0])
    ).fetchone()
    if previous is not None:
        if previous[0] != row[2]:
            raise RequestRecordError("record_id: conflicting persisted retry")
        return
    connection.execute(
        "INSERT INTO request_records_v1(record_id, run_id, record_json) VALUES (?, ?, ?)", row
    )


def persist_canonical_records(database_path: str, context: "RunContext") -> str:
    """Persist one explicit run atomically in separate v1 tables; retries are idempotent."""
    rows = _canonical_rows(context)
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            _ensure_canonical_schema(connection)
            connection.execute(
                "INSERT OR IGNORE INTO request_runs_v1(run_id, schema_version) VALUES (?, 1)", (context.run_id,)
            )
            for row in rows:
                _insert_canonical_row(connection, row)
    return context.run_id


def fetch_canonical_records(database_path: str, run_id: str) -> list["RequestRecord"]:
    """Read and revalidate an ordered canonical snapshot without changing legacy tables."""
    from je_action_core.request_record import RequestRecordError, validate_request_record

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            _ensure_canonical_schema(connection)
        rows = connection.execute(
            "SELECT record_id, record_json FROM request_records_v1 WHERE run_id = ? ORDER BY sequence", (run_id,)
        ).fetchall()
    records = []
    for identifier, payload in rows:
        try:
            record = validate_request_record(json.loads(payload))
        except json.JSONDecodeError as error:
            raise RequestRecordError("record_json: malformed stored JSON") from error
        if record["run_id"] != run_id or record["record_id"] != identifier:
            raise RequestRecordError("record_json: stored identity does not match its index")
        records.append(record)
    return records
