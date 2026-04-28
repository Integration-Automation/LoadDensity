from typing import Any, Dict, Optional


class ProxyFastHTTPUser:
    """
    代理使用者類別
    Proxy Fast HTTP User class

    用來保存使用者細節與任務設定。
    Used to store user details and tasks configuration.
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
        """
        設定使用者細節與任務
        Configure user details and tasks
        """
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks
        self.host = host
        self.extra = {k: v for k, v in kwargs.items() if k not in {"variables", "csv_sources"}}
