from typing import Any, Dict, Optional


class ProxySocketUser:
    """
    代理 Socket 使用者類別 (TCP/UDP)
    Proxy raw socket User class
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
