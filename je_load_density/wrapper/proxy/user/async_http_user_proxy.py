from typing import Any, Dict, Optional


class ProxyAsyncHttpUser:
    """Proxy for the async HTTP / HTTP-2 user template (httpx-backed)."""

    def __init__(self) -> None:
        self.user_detail_dict: Optional[Dict[str, Any]] = None
        self.tasks: Optional[Any] = None
        self.host: Optional[str] = None
        self.http2: bool = False
        self.extra: Dict[str, Any] = {}

    def configure(
        self,
        user_detail_dict: Dict[str, Any],
        tasks: Optional[Any] = None,
        host: Optional[str] = None,
        http2: bool = False,
        **kwargs: Any,
    ) -> None:
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks
        self.host = host
        self.http2 = bool(http2)
        self.extra = {k: v for k, v in kwargs.items() if k not in {"variables", "csv_sources"}}
