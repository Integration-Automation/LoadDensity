"""
DB seed / cleanup fixtures.

Runs a list of SQL statements before and after a load test via
SQLAlchemy (lazy import). Supports rollback by recording a teardown
script the operator can re-run if needed.
"""

from typing import Any, Dict, List, Optional


def _import_sqlalchemy():
    try:
        from sqlalchemy import create_engine, text
    except ImportError as error:
        raise RuntimeError(
            "sqlalchemy is required for db fixtures; install with: pip install sqlalchemy"
        ) from error
    return create_engine, text


def _execute_all(database_url: str, statements: List[str]) -> None:
    """Run ``statements`` in one transaction, then dispose the engine even if one fails.

    Without the dispose the pool kept its connections open, and a SQLite file stayed locked.
    """
    create_engine, text = _import_sqlalchemy()
    engine = create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    finally:
        engine.dispose()


def apply_fixture(
    database_url: str,
    setup_sql: Optional[List[str]] = None,
    teardown_sql: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run setup_sql, return a handle that lets the caller run teardown later.

    Example::

        fixture = apply_fixture(
            "postgresql://...",
            setup_sql=["INSERT INTO users (email) VALUES ('x@y')"],
            teardown_sql=["DELETE FROM users WHERE email = 'x@y'"],
        )
        try:
            run_load_test(...)
        finally:
            run_teardown(fixture)
    """
    _execute_all(database_url, list(setup_sql or []))
    return {
        "database_url": database_url,
        "teardown_sql": list(teardown_sql or []),
    }


def run_teardown(fixture: Dict[str, Any]) -> None:
    """Execute every teardown statement recorded in ``fixture``."""
    teardown = fixture.get("teardown_sql") or []
    if not teardown:
        return
    _execute_all(fixture["database_url"], list(teardown))
