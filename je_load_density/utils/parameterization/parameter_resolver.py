import csv
import itertools
import os
import re
import threading
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional

_PLACEHOLDER_PATTERN = re.compile(r"\$\{([^}]+)\}")
_FUNCTION_PATTERN = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)$")


class ParameterResolver:
    """
    參數解析器
    Parameter resolver for ${var} placeholders in load test definitions.

    Supports:
        ${env.NAME}            -> environment variable
        ${var.key}             -> registered variable
        ${csv.source.column}   -> next row from CSV source (cycled)
        ${faker.method}        -> faker output (if faker installed)
        ${func(arg)}           -> built-in helpers (uuid, now, randint(min,max))

    Unknown placeholders are left in place so missing data is visible.
    """

    def __init__(self) -> None:
        self._variables: Dict[str, Any] = {}
        self._csv_sources: Dict[str, Iterator[Dict[str, str]]] = {}
        self._lock = threading.Lock()
        self._faker = None

    def register_variable(self, name: str, value: Any) -> None:
        with self._lock:
            self._variables[name] = value

    def register_csv_source(self, name: str, file_path: str, cycle: bool = True) -> None:
        rows = self._read_csv(file_path)
        with self._lock:
            self._csv_sources[name] = itertools.cycle(rows) if cycle else iter(rows)

    @staticmethod
    def _read_csv(file_path: str) -> List[Dict[str, str]]:
        with open(file_path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            return list(reader)

    def _next_csv_row(self, name: str) -> Optional[Dict[str, str]]:
        with self._lock:
            source = self._csv_sources.get(name)
            if source is None:
                return None
            try:
                return next(source)
            except StopIteration:
                return None

    def _resolve_token(self, token: str) -> Optional[str]:
        token = token.strip()
        if not token:
            return None

        function_match = _FUNCTION_PATTERN.match(token)
        if function_match:
            return self._resolve_function(function_match.group(1), function_match.group(2))

        if "." not in token:
            value = self._variables.get(token)
            return None if value is None else str(value)

        prefix, _, rest = token.partition(".")
        prefix = prefix.lower()

        if prefix == "env":
            return os.environ.get(rest)
        if prefix == "var":
            value = self._variables.get(rest)
            return None if value is None else str(value)
        if prefix == "csv":
            source_name, _, column = rest.partition(".")
            row = self._next_csv_row(source_name)
            if row is None:
                return None
            return row.get(column)
        if prefix == "faker":
            return self._resolve_faker(rest)
        return None

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
        Non-string scalar types pass through unchanged.
        """
        if isinstance(value, str):
            return self._resolve_string(value)
        if isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.resolve(item) for item in value)
        return value

    def _resolve_string(self, value: str) -> str:
        def repl(match: re.Match) -> str:
            resolved = self._resolve_token(match.group(1))
            return match.group(0) if resolved is None else resolved

        return _PLACEHOLDER_PATTERN.sub(repl, value)

    def clear(self) -> None:
        with self._lock:
            self._variables.clear()
            self._csv_sources.clear()


parameter_resolver = ParameterResolver()


def resolve(value: Any) -> Any:
    return parameter_resolver.resolve(value)


def register_variable(name: str, value: Any) -> None:
    parameter_resolver.register_variable(name, value)


def register_csv_source(name: str, file_path: str, cycle: bool = True) -> None:
    parameter_resolver.register_csv_source(name, file_path, cycle)


def register_variables(variables: Dict[str, Any]) -> None:
    for key, value in variables.items():
        parameter_resolver.register_variable(key, value)


def register_csv_sources(sources: Iterable[Dict[str, Any]]) -> None:
    for source in sources:
        name = source.get("name")
        file_path = source.get("file_path")
        cycle = source.get("cycle", True)
        if name and file_path:
            parameter_resolver.register_csv_source(name, file_path, cycle)
