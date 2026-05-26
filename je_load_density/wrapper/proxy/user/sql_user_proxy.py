from typing import Any, Dict, Optional


class ProxySqlUser:
    """Proxy for the SQL DB user template."""

    def __init__(self) -> None:
        self.user_detail_dict: Optional[Dict[str, Any]] = None
        self.tasks: Optional[Any] = None
        self.connection_string: Optional[str] = None
        self.extra: Dict[str, Any] = {}

    def configure(
        self,
        user_detail_dict: Dict[str, Any],
        tasks: Optional[Any] = None,
        connection_string: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks
        self.connection_string = connection_string
        self.extra = {k: v for k, v in kwargs.items() if k not in {"variables", "csv_sources"}}
