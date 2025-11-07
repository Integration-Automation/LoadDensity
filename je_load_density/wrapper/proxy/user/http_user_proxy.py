from typing import Dict, Any, Callable, List, Optional


class ProxyHTTPUser:
    """
    代理 HTTP 使用者類別
    Proxy HTTP User class

    用來保存使用者細節與任務設定。
    Used to store user details and tasks configuration.
    """

    def __init__(self) -> None:
        # 使用者細節 (User details)
        self.user_detail_dict: Optional[Dict[str, Any]] = None
        # 任務列表 (Tasks list, 可是函式或其他可呼叫物件)
        self.tasks: Optional[List[Callable]] = None

    def configure(self, user_detail_dict: Dict[str, Any], tasks: List[Callable]) -> None:
        """
        設定使用者細節與任務
        Configure user details and tasks

        :param user_detail_dict: 使用者細節字典 (User details dictionary)
        :param tasks: 任務列表 (List of tasks, functions or callables)
        """
        self.user_detail_dict = user_detail_dict
        self.tasks = tasks

    def run_tasks(self) -> None:
        """
        執行所有任務
        Run all tasks
        """
        if not self.tasks:
            print("No tasks configured.")
            return
        for task in self.tasks:
            if callable(task):
                task(self.user_detail_dict)