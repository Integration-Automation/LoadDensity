import copy
import csv
import itertools
import os
import re
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

_PLACEHOLDER_PATTERN = re.compile(r"\$\{([^}]+)\}")
_FUNCTION_PATTERN = re.compile(r"^([a-zA-Z_]\w*)\((.*)\)$")


def _stringify(value: Any) -> Optional[str]:
    return None if value is None else str(value)


class _RowProvider:
    """Serialize advancement across all users sharing a cached data source."""

    def __init__(self, rows: List[Dict[str, Any]], cycle: bool) -> None:
        self._rows = itertools.cycle(rows) if cycle else iter(rows)
        self._lock = threading.Lock()

    def next_row(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(next(self._rows, None))


_ResolvedRows = Dict[Tuple[str, str], Optional[Dict[str, Any]]]


class ParameterResolver:
    """
    參數解析器
    Parameter resolver for ${var} placeholders in load test definitions.

    Supports:
        ${env.NAME}            -> environment variable
        ${var.key}             -> registered variable
        ${session.key}         -> per-user session variable
        ${csv.source.column}   -> one row per source per resolve call (cycled)
        ${faker.method}        -> faker output (if faker installed)
        ${func(arg)}           -> built-in helpers (uuid, now, randint(min,max))

    Unknown placeholders are left in place so missing data is visible.
    """

    def __init__(self) -> None:
        self._variables: Dict[str, Any] = {}
        self._session_variables: Dict[str, Any] = {}
        self._csv_sources: Dict[str, _RowProvider] = {}
        self._db_sources: Dict[str, _RowProvider] = {}
        self._lock = threading.Lock()
        self._faker = None

    def register_variable(self, name: str, value: Any) -> None:
        """Set a variable in this resolver, without changing another user's state."""
        with self._lock:
            self._variables[name] = value

    def register_session_variable(self, name: str, value: Any) -> None:
        """Set a value accessible through the separate ${session.NAME} namespace."""
        with self._lock:
            self._session_variables[name] = value

    def fork(self) -> "ParameterResolver":
        """Copy variable/session state; share synchronized CSV/DB row providers."""
        child = ParameterResolver()
        with self._lock:
            child._variables = copy.deepcopy(self._variables)
            child._session_variables = copy.deepcopy(self._session_variables)
            child._csv_sources = dict(self._csv_sources)
            child._db_sources = dict(self._db_sources)
        return child

    def register_csv_source(self, name: str, file_path: str, cycle: bool = True) -> None:
        """Cache CSV rows in a provider shared by subsequently forked users."""
        rows = self._read_csv(file_path)
        with self._lock:
            self._csv_sources[name] = _RowProvider(rows, cycle)

    def register_db_source(self, name: str, connection_string: str,
                           query: str, cycle: bool = True) -> None:
        """
        Register a parameter source backed by a SQL query.

        A recursive resolve call reuses one row for every ``${db.NAME.column}``
        field. Forked resolvers share row advancement. SQLAlchemy is a soft dependency.
        """
        rows = self._read_db(connection_string, query)
        with self._lock:
            self._db_sources[name] = _RowProvider(rows, cycle)

    @staticmethod
    def _read_db(connection_string: str, query: str) -> List[Dict[str, Any]]:
        try:
            from sqlalchemy import create_engine, text
        except ImportError as error:
            raise RuntimeError(
                "SQLAlchemy is required for ${db.*}; install with: pip install sqlalchemy"
            ) from error
        engine = create_engine(connection_string, future=True)
        try:
            with engine.connect() as connection:
                result = connection.execute(text(query))
                keys = list(result.keys())
                return [dict(zip(keys, row)) for row in result.fetchall()]
        finally:
            engine.dispose()

    @staticmethod
    def _read_csv(file_path: str) -> List[Dict[str, str]]:
        with open(file_path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            return list(reader)

    def _next_csv_row(self, name: str) -> Optional[Dict[str, str]]:
        with self._lock:
            source = self._csv_sources.get(name)
        return source.next_row() if source is not None else None

    def _next_db_row(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            source = self._db_sources.get(name)
        return source.next_row() if source is not None else None

    def _variable(self, name: str, session: bool = False) -> Optional[str]:
        with self._lock:
            values = self._session_variables if session else self._variables
            return _stringify(values.get(name))

    def _resolve_token(self, token: str, rows: _ResolvedRows) -> Optional[str]:
        token = token.strip()
        if not token:
            return None

        function_match = _FUNCTION_PATTERN.match(token)
        if function_match:
            return self._resolve_function(function_match.group(1), function_match.group(2))

        if "." not in token:
            return self._variable(token)

        prefix, _, rest = token.partition(".")
        return self._resolve_prefixed(prefix.lower(), rest, rows)

    def _resolve_prefixed(self, prefix: str, rest: str, rows: _ResolvedRows) -> Optional[str]:
        if prefix == "env":
            return os.environ.get(rest)
        if prefix == "var":
            return self._variable(rest)
        if prefix == "session":
            return self._variable(rest, session=True)
        if prefix == "csv":
            return self._resolve_csv(rest, rows)
        if prefix == "db":
            return self._resolve_db(rest, rows)
        if prefix == "faker":
            return self._resolve_faker(rest)
        return None

    def _resolve_csv(self, rest: str, rows: _ResolvedRows) -> Optional[str]:
        source_name, _, column = rest.partition(".")
        key = ("csv", source_name)
        if key not in rows:
            rows[key] = self._next_csv_row(source_name)
        row = rows[key]
        return None if row is None else row.get(column)

    def _resolve_db(self, rest: str, rows: _ResolvedRows) -> Optional[str]:
        source_name, _, column = rest.partition(".")
        key = ("db", source_name)
        if key not in rows:
            rows[key] = self._next_db_row(source_name)
        row = rows[key]
        if row is None:
            return None
        return _stringify(row.get(column))

    def _resolve_function(self, name: str, raw_args: str) -> Optional[str]:
        name = name.lower()
        args = [a.strip() for a in raw_args.split(",")] if raw_args else []
        if name == "uuid":
            import uuid
            return str(uuid.uuid4())
        if name == "now":
            import datetime
            return datetime.datetime.now().isoformat(timespec="seconds")
        if name == "randint" and len(args) == 2:
            import secrets
            low, high = int(args[0]), int(args[1])
            return str(secrets.randbelow(high - low + 1) + low)
        return None

    def _resolve_faker(self, method: str) -> Optional[str]:
        if self._faker is None:
            try:
                from faker import Faker
            except ImportError:
                return None
            self._faker = Faker()
        provider = getattr(self._faker, method, None)
        if provider is None:
            return None
        try:
            return str(provider())
        except Exception:
            return None

    def resolve(self, value: Any) -> Any:
        """
        Recursively resolve placeholders inside strings, dicts, lists, and tuples.
        One row per source is reused throughout this call. Non-string scalar
        types pass through unchanged; separate calls advance to subsequent rows.
        """
        return self._resolve_value(value, {})

    def _resolve_value(self, value: Any, rows: _ResolvedRows) -> Any:
        if isinstance(value, str):
            return self._resolve_string(value, rows)
        if isinstance(value, dict):
            return {key: self._resolve_value(item, rows) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(item, rows) for item in value]
        if isinstance(value, tuple):
            return tuple(self._resolve_value(item, rows) for item in value)
        return value

    def _resolve_string(self, value: str, rows: _ResolvedRows) -> str:
        def repl(match: re.Match) -> str:
            resolved = self._resolve_token(match.group(1), rows)
            return match.group(0) if resolved is None else resolved

        return _PLACEHOLDER_PATTERN.sub(repl, value)

    def clear(self) -> None:
        """Clear this resolver; already forked users retain their state and providers."""
        with self._lock:
            self._variables.clear()
            self._session_variables.clear()
            self._csv_sources.clear()
            self._db_sources.clear()


_default_resolver = ParameterResolver()
_active_resolver: ContextVar[Optional[ParameterResolver]] = ContextVar("load_density_parameter_resolver", default=None)


def get_resolver() -> ParameterResolver:
    """Return the explicit thread/task/greenlet resolver, or the legacy default."""
    selected = _active_resolver.get()
    return _default_resolver if selected is None else selected


@contextmanager
def use_resolver(resolver: ParameterResolver) -> Iterator[ParameterResolver]:
    """Select an explicit user's resolver for this scope and restore it on exit."""
    if not isinstance(resolver, ParameterResolver):
        raise TypeError("resolver must be a ParameterResolver instance")
    token = _active_resolver.set(resolver)
    try:
        yield resolver
    finally:
        _active_resolver.reset(token)


class _ResolverFacade:
    """Retain legacy imports while selecting state when each method is called."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_resolver(), name)

    def resolve(self, value: Any) -> Any:
        return get_resolver().resolve(value)

    def fork(self) -> ParameterResolver:
        return get_resolver().fork()

    def register_variable(self, name: str, value: Any) -> None:
        get_resolver().register_variable(name, value)

    def register_session_variable(self, name: str, value: Any) -> None:
        get_resolver().register_session_variable(name, value)

    def register_csv_source(self, name: str, file_path: str, cycle: bool = True) -> None:
        get_resolver().register_csv_source(name, file_path, cycle)

    def register_db_source(self, name: str, connection_string: str, query: str, cycle: bool = True) -> None:
        get_resolver().register_db_source(name, connection_string, query, cycle)

    def clear(self) -> None:
        get_resolver().clear()


parameter_resolver = _ResolverFacade()


def resolve(value: Any) -> Any:
    """Resolve a request using the selected resolver, falling back to legacy state."""
    return parameter_resolver.resolve(value)


def register_variable(name: str, value: Any) -> None:
    """Register a variable in the selected resolver."""
    parameter_resolver.register_variable(name, value)


def register_session_variable(name: str, value: Any) -> None:
    """Register a variable in the selected resolver's session namespace."""
    parameter_resolver.register_session_variable(name, value)


def register_csv_source(name: str, file_path: str, cycle: bool = True) -> None:
    """Register cached CSV data in the selected resolver."""
    parameter_resolver.register_csv_source(name, file_path, cycle)


def register_variables(variables: Dict[str, Any]) -> None:
    """Register a mapping of variables in the selected resolver."""
    for key, value in variables.items():
        parameter_resolver.register_variable(key, value)


def register_csv_sources(sources: Iterable[Dict[str, Any]]) -> None:
    """Register named CSV source specifications in the selected resolver."""
    for source in sources:
        name = source.get("name")
        file_path = source.get("file_path")
        cycle = source.get("cycle", True)
        if name and file_path:
            parameter_resolver.register_csv_source(name, file_path, cycle)


def register_db_source(name: str, connection_string: str,
                       query: str, cycle: bool = True) -> None:
    """Register cached query data in the selected resolver."""
    parameter_resolver.register_db_source(name, connection_string, query, cycle)


def register_db_sources(sources: Iterable[Dict[str, Any]]) -> None:
    """Register named database source specifications in the selected resolver."""
    for source in sources:
        name = source.get("name")
        connection_string = source.get("connection_string")
        query = source.get("query")
        cycle = source.get("cycle", True)
        if name and connection_string and query:
            parameter_resolver.register_db_source(name, connection_string, query, cycle)
