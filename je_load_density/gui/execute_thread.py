from PySide6.QtCore import QThread
from je_load_density.wrapper.start_wrapper.start_test import start_test


class LoadDensityThread(QThread):

    def __init__(self):
        super().__init__()
        self.url = None
        self.test_time = None
        self.user_count = None
        self.spawn_rate = None
        self.method = None

    def run(self):
        start_test(
            {
                "user": "fast_http_user",
            },
            self.user_count, self.spawn_rate, self.test_time,
            **{
                "tasks": {
                    self.method: {"request_url": self.url},
                }
            }
        )