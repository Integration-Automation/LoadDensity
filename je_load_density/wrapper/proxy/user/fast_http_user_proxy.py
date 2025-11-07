from typing import Dict, Any, List, Optional


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
        # 任務列表 (Tasks list)
        self.tasks: Optional[List[Any]] = None

    def configure(self, user_detail_dict: Dict[str, Any], tasks: List[Any]) -> None:
        """
        設定使用者細節與任務
        Configure user details and tasks

        :param user_detail_dict: 使用者細節字典 (User details dictionary)
        :param tasks: 任務列表 (List of tasks)
        """
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks