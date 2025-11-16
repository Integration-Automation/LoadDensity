from PySide6.QtCore import QThread
from je_load_density.wrapper.start_wrapper.start_test import start_test

# 定義常數，避免硬編碼字串
# Define constant to avoid hard-coded string
DEFAULT_USER_TYPE = "fast_http_user"


class LoadDensityGUIThread(QThread):
    """
    GUI 測試執行緒
    GUI Test Thread

    用於在背景執行負載測試，避免阻塞主介面。
    Used to run load tests in the background without blocking the main GUI.
    """

    def __init__(self,
                 request_url: str = None,
                 test_duration: int = None,
                 user_count: int = None,
                 spawn_rate: int = None,
                 http_method: str = None):
        """
        初始化執行緒參數
        Initialize thread parameters

        :param request_url: 測試目標 URL (Target request URL)
        :param test_duration: 測試持續時間 (Test duration in seconds)
        :param user_count: 使用者數量 (Number of simulated users)
        :param spawn_rate: 使用者生成速率 (User spawn rate)
        :param http_method: HTTP 方法 (HTTP method, e.g., "GET", "POST")
        """
        super().__init__()
        self.request_url = request_url
        self.test_duration = test_duration
        self.user_count = user_count
        self.spawn_rate = spawn_rate
        self.http_method = http_method

    def run(self):
        """
        執行負載測試
        Run the load test
        """
        if not self.request_url or not self.http_method:
            # 基本檢查，避免傳入 None
            # Basic validation to avoid None values
            raise ValueError("Request URL and HTTP method must be provided.")

        start_test(
            {"user": DEFAULT_USER_TYPE},  # 使用者類型 (User type)
            self.user_count,
            self.spawn_rate,
            self.test_duration,
            tasks={
                self.http_method: {"request_url": self.request_url}
            }
        )