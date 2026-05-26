import pytest

from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_db_source,
)


@pytest.fixture
def reset_resolver():
    parameter_resolver.clear()
    yield
    parameter_resolver.clear()


def test_db_source_cycles_rows(tmp_path, reset_resolver):
    pytest.importorskip("sqlalchemy")
    db_path = tmp_path / "users.db"
    from sqlalchemy import create_engine, text
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (email TEXT, name TEXT)"))
        conn.execute(text("INSERT INTO users VALUES ('a@x', 'A'), ('b@x', 'B')"))

    register_db_source("users", f"sqlite:///{db_path}",
                       "SELECT email, name FROM users")

    first = parameter_resolver.resolve("${db.users.email}")
    second = parameter_resolver.resolve("${db.users.email}")
    third = parameter_resolver.resolve("${db.users.email}")

    assert first in {"a@x", "b@x"}
    assert second in {"a@x", "b@x"}
    assert first != second
    assert third in {"a@x", "b@x"}


def test_db_source_no_register_returns_placeholder(reset_resolver):
    value = parameter_resolver.resolve("${db.missing.name}")
    assert value == "${db.missing.name}"


def test_db_source_unknown_column(tmp_path, reset_resolver):
    pytest.importorskip("sqlalchemy")
    db_path = tmp_path / "x.db"
    from sqlalchemy import create_engine, text
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (id INTEGER)"))
        conn.execute(text("INSERT INTO t VALUES (1)"))
    register_db_source("t", f"sqlite:///{db_path}", "SELECT id FROM t")
    value = parameter_resolver.resolve("${db.t.missing}")
    assert value == "${db.t.missing}"
