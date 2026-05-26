from typing import Any, Dict, List, Optional


class ProxyKafkaUser:
    """Proxy for the Kafka user template."""

    def __init__(self) -> None:
        self.user_detail_dict: Optional[Dict[str, Any]] = None
        self.tasks: Optional[Any] = None
        self.bootstrap_servers: Optional[List[str]] = None
        self.extra: Dict[str, Any] = {}

    def configure(
        self,
        user_detail_dict: Dict[str, Any],
        tasks: Optional[Any] = None,
        bootstrap_servers: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks
        self.bootstrap_servers = bootstrap_servers
        self.extra = {k: v for k, v in kwargs.items() if k not in {"variables", "csv_sources"}}
