from typing import Any, Dict, Optional


class ProxyWebSocketUser:
    """
    代理 WebSocket 使用者類別
    Proxy WebSocket User class
    """

    def __init__(self) -> None:
        self.user_detail_dict: Optional[Dict[str, Any]] = None
        self.tasks: Optional[Any] = None
        self.host: Optional[str] = None
        self.extra: Dict[str, Any] = {}

    def configure(
        self,
        user_detail_dict: Dict[str, Any],
        tasks: Optional[Any] = None,
        host: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks
        self.host = host
        self.extra = {k: v for k, v in kwargs.items() if k not in {"variables", "csv_sources"}}
