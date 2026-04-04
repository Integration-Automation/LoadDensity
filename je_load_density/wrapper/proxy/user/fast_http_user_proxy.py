from typing import Dict, Any, Optional


class ProxyFastHTTPUser:
    """
    代理使用者類別
    Proxy Fast HTTP User class

    用來保存使用者細節與任務設定。
    Used to store user details and tasks configuration.
    """

    def __init__(self) -> None:
        # 使用者細節 (User details)
        self.user_detail_dict: Optional[Dict[str, Any]] = None
        # 任務字典 (Tasks dictionary, HTTP method -> request config)
        self.tasks: Optional[Dict[str, Dict[str, Any]]] = None

    def configure(self, user_detail_dict: Dict[str, Any], tasks: Dict[str, Dict[str, Any]]) -> None:
        """
        設定使用者細節與任務
        Configure user details and tasks

        :param user_detail_dict: 使用者細節字典 (User details dictionary)
        :param tasks: 任務字典 (Tasks dictionary, e.g. {"get": {"request_url": "..."}, ...})
        """
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks