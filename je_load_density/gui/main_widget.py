import logging
import queue
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QTextEdit, QVBoxLayout, QLabel, QMessageBox
)

from je_load_density.gui.load_density_gui_thread import LoadDensityGUIThread
from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.gui.log_to_ui_filter import InterceptAllFilter, log_message_queue


class LoadDensityWidget(QWidget):
    """
    負載測試 GUI 控制元件
    Load Test GUI Widget

    提供使用者輸入測試參數並啟動負載測試，
    並將日誌訊息即時顯示在 GUI 中。
    Provides input fields for test parameters, starts load tests,
    and displays log messages in real-time.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # === 表單區域 (Form Section) ===
        form_layout = QFormLayout()

        # URL 輸入框 (Target URL input)
        self.url_input = QLineEdit()

        # 測試時間 (Test duration, must be int)
        self.test_time_input = QLineEdit()
        self.test_time_input.setValidator(QIntValidator())

        # 使用者數量 (User count)
        self.user_count_input = QLineEdit()
        self.user_count_input.setValidator(QIntValidator())

        # 生成速率 (Spawn rate)
        self.spawn_rate_input = QLineEdit()
        self.spawn_rate_input.setValidator(QIntValidator())

        # HTTP 方法選擇 (HTTP method selection)
        self.method_combobox = QComboBox()
        self.method_combobox.addItems([
            language_wrapper.language_word_dict.get("get"),
            language_wrapper.language_word_dict.get("post"),
            language_wrapper.language_word_dict.get("put"),
            language_wrapper.language_word_dict.get("patch"),
            language_wrapper.language_word_dict.get("delete"),
            language_wrapper.language_word_dict.get("head"),
            language_wrapper.language_word_dict.get("options"),
        ])

        # 將元件加入表單 (Add widgets to form layout)
        form_layout.addRow(language_wrapper.language_word_dict.get("url"), self.url_input)
        form_layout.addRow(language_wrapper.language_word_dict.get("test_time"), self.test_time_input)
        form_layout.addRow(language_wrapper.language_word_dict.get("user_count"), self.user_count_input)
        form_layout.addRow(language_wrapper.language_word_dict.get("spawn_rate"), self.spawn_rate_input)
        form_layout.addRow(language_wrapper.language_word_dict.get("test_method"), self.method_combobox)

        # === 啟動按鈕 (Start button) ===
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("start_button"))
        self.start_button.clicked.connect(self.run_load_density)

        # === 日誌面板 (Log panel) ===
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)

        # === 主版面配置 (Main layout) ===
        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.start_button)
        main_layout.addWidget(QLabel(language_wrapper.language_word_dict.get("log")))
        main_layout.addWidget(self.log_panel)

        # === 執行緒與計時器 (Thread & Timer) ===
        self.run_load_density_thread: Optional[LoadDensityGUIThread] = None
        self.pull_log_timer = QTimer()
        self.pull_log_timer.setInterval(50)  # 稍微放大間隔，避免 UI 卡頓
        self.pull_log_timer.timeout.connect(self.add_text_to_log)

        self.setLayout(main_layout)

    def run_load_density(self) -> None:
        """
        啟動負載測試
        Start the load test
        """
        try:
            test_time = int(self.test_time_input.text())
            user_count = int(self.user_count_input.text())
            spawn_rate = int(self.spawn_rate_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "請輸入有效的數字\nPlease enter valid numbers")
            return

        self.run_load_density_thread = LoadDensityGUIThread()
        self.run_load_density_thread.request_url = self.url_input.text()
        self.run_load_density_thread.test_duration = test_time
        self.run_load_density_thread.user_count = user_count
        self.run_load_density_thread.spawn_rate = spawn_rate
        self.run_load_density_thread.http_method = self.method_combobox.currentText().lower()

        # 設定日誌攔截器 (Attach log filter)
        root_logger = logging.getLogger("root")
        log_handler_list = [handler for handler in root_logger.handlers if handler.name == "log_reader"]
        if log_handler_list:
            log_handler = log_handler_list[0]
            # 避免重複新增 Filter (Prevent duplicate filters)
            if not any(isinstance(f, InterceptAllFilter) for f in log_handler.filters):
                log_handler.addFilter(InterceptAllFilter())

        # 啟動執行緒與計時器 (Start thread & timer)
        self.run_load_density_thread.start()
        self.pull_log_timer.start()
        self.log_panel.clear()

    def add_text_to_log(self) -> None:
        """
        將日誌訊息加入到 GUI 面板
        Append log messages to GUI panel
        """
        while not log_message_queue.empty():
            self.log_panel.append(log_message_queue.get_nowait())