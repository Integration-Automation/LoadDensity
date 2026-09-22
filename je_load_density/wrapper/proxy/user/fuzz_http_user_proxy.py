from typing import Any, Dict, Optional


class ProxyFuzzHttpUser:
    """Proxy for the fuzzing HTTP user template."""

    def __init__(self) -> None:
        self.user_detail_dict: Optional[Dict[str, Any]] = None
        self.tasks: Optional[Any] = None
        self.connection: Optional[Dict[str, Any]] = None
        self.extra: Dict[str, Any] = {}

    def configure(
        self,
        user_detail_dict: Dict[str, Any],
        tasks: Optional[Any] = None,
        connection: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks
        self.connection = connection
        self.extra = {k: v for k, v in kwargs.items() if k not in {"variables", "csv_sources"}}
