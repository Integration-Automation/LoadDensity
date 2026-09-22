"""
Neo4j user template (neo4j driver, lazy import).

Each task entry::

    {"method": "connect", "uri": "bolt://127.0.0.1:7687",
     "user": "neo4j", "password": "neo4j"}
    {"method": "run", "cypher": "MATCH (n) RETURN count(n)"}
    {"method": "close"}
"""

from typing import Any, Callable, Dict, Optional

from je_load_density.wrapper.user_template._protocol_base import (
    ProtocolUserBase,
    make_setter,
)


def _import_neo4j():
    try:
        from neo4j import GraphDatabase
    except ImportError as error:
        raise RuntimeError(
            "neo4j is required for Neo4jUser; install with: pip install neo4j"
        ) from error
    return GraphDatabase


class Neo4jUserWrapper(ProtocolUserBase):
    """Locust user driving neo4j-driver calls."""

    _proxy_key = "neo4j_user"
    _request_type = "NEO4J"
    host = "bolt://127.0.0.1:7687"

    def __init__(self, environment):
        super().__init__(environment)
        self._driver = None

    def _connect(self, step: Dict[str, Any]) -> int:
        graph = _import_neo4j()
        self._driver = graph.driver(
            step.get("uri", self.host),
            auth=(step.get("user", "neo4j"), step.get("password", "neo4j")),
        )
        return 0

    def _run(self, step: Dict[str, Any]) -> int:
        if self._driver is None:
            raise RuntimeError("neo4j driver not connected")
        with self._driver.session(database=step.get("database")) as session:
            result = session.run(step["cypher"], step.get("parameters") or {})
            records = list(result)
            return sum(len(str(record)) for record in records)

    def _close(self, _: Dict[str, Any]) -> int:
        if self._driver is not None:
            self._driver.close()
            self._driver = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {"connect": self._connect, "run": self._run, "close": self._close}.get(method)


set_wrapper_neo4j_user = make_setter("neo4j_user", Neo4jUserWrapper)
