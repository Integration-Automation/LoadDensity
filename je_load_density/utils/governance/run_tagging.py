"""
Run tagging — augment the SQLite persistence store with tag tables.

Lets a CI pipeline attach arbitrary tag={owner, environment, branch,
ticket} pairs to each run, then filter or search later.
"""

import sqlite3
from contextlib import closing
from typing import Any, Dict, List

_SCHEMA = """
CREATE TABLE IF NOT EXISTS load_density_run_tags (
    run_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (run_id, key)
);
CREATE INDEX IF NOT EXISTS idx_tags_key_value
    ON load_density_run_tags (key, value);
"""


def _connect(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    with connection:
        connection.executescript(_SCHEMA)


def tag_run(database_path: str, run_id: int, tags: Dict[str, str]) -> None:
    """Attach (or overwrite) tag key/value pairs on ``run_id``."""
    with closing(_connect(database_path)) as connection:
        _ensure_schema(connection)
        with connection:
            for key, value in tags.items():
                connection.execute(
                    "INSERT OR REPLACE INTO load_density_run_tags (run_id, key, value)"
                    " VALUES (?, ?, ?)",
                    (run_id, key, str(value)),
                )


def list_tags(database_path: str, run_id: int) -> Dict[str, str]:
    """Return the tags attached to ``run_id``."""
    with closing(_connect(database_path)) as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            "SELECT key, value FROM load_density_run_tags WHERE run_id = ?",
            (run_id,),
        )
        return {row["key"]: row["value"] for row in cursor.fetchall()}


def search_runs_by_tag(
    database_path: str, key: str, value: str,
) -> List[Dict[str, Any]]:
    """Return runs whose tag matches ``key=value``."""
    with closing(_connect(database_path)) as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            "SELECT r.id, r.started_at, r.label FROM load_density_runs r "
            "JOIN load_density_run_tags t ON t.run_id = r.id "
            "WHERE t.key = ? AND t.value = ? ORDER BY r.id DESC",
            (key, str(value)),
        )
        return [dict(row) for row in cursor.fetchall()]
