from typing import Any, Dict, List, Optional


class ProxyCassandraUser:
    """Proxy for the Cassandra / ScyllaDB user template."""

    def __init__(self) -> None:
        self.user_detail_dict: Optional[Dict[str, Any]] = None
        self.tasks: Optional[Any] = None
        self.contact_points: Optional[List[str]] = None
        self.keyspace: Optional[str] = None
        self.extra: Dict[str, Any] = {}

    def configure(
        self,
        user_detail_dict: Dict[str, Any],
        tasks: Optional[Any] = None,
        contact_points: Optional[List[str]] = None,
        keyspace: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks
        self.contact_points = contact_points
        self.keyspace = keyspace
        self.extra = {k: v for k, v in kwargs.items() if k not in {"variables", "csv_sources"}}
