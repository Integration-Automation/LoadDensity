import logging

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QComboBox, QPushButton, QTextEdit, QVBoxLayout, QLabel

from je_load_density.gui.execute_thread import LoadDensityThread
from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.log_to_ui_filter import InterceptAllFilter, locust_log_queue


class LoadDensityWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        # from
        form_layout = QFormLayout()
        self.url_input = QLineEdit()
        self.test_time_input = QLineEdit()
        self.test_time_input.setValidator(QIntValidator())
        self.user_count_input = QLineEdit()
        self.user_count_input.setValidator(QIntValidator())
        self.spawn_rate_input = QLineEdit()
        self.spawn_rate_input.setValidator(QIntValidator())
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
        form_layout.addRow(language_wrapper.language_word_dict.get("url"), self.url_input)
        form_layout.addRow(language_wrapper.language_word_dict.get("test_time"), self.test_time_input)
        form_layout.addRow(language_wrapper.language_word_dict.get("user_count"), self.user_count_input)
        form_layout.addRow(language_wrapper.language_word_dict.get("spawn_rate"), self.spawn_rate_input)
        form_layout.addRow(language_wrapper.language_word_dict.get("test_method"), self.method_combobox)

        self.start_button = QPushButton(language_wrapper.language_word_dict.get("start_button"))
        self.start_button.clicked.connect(self.run_load_density)

        # Log panel
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)

        # Add widget to vertical layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.start_button)
        main_layout.addWidget(QLabel(language_wrapper.language_word_dict.get("log")))
        main_layout.addWidget(self.log_panel)

        # Param
        self.run_load_density_thread = None
        self.pull_log_timer = QTimer()
        self.pull_log_timer.setInterval(20)
        self.pull_log_timer.timeout.connect(self.add_text_to_log)

        self.setLayout(main_layout)

    def run_load_density(self):
        self.run_load_density_thread = LoadDensityThread()
        self.run_load_density_thread.url = self.url_input.text()
        self.run_load_density_thread.test_time = int(self.test_time_input.text())
        self.run_load_density_thread.user_count = int(self.user_count_input.text())
        self.run_load_density_thread.spawn_rate = int(self.spawn_rate_input.text())
        self.run_load_density_thread.method = self.method_combobox.currentText().lower()
        log_handler_list = [handler for handler in logging.getLogger("root").handlers if handler.name == "log_reader"]
        if log_handler_list:
            log_handler = log_handler_list[0]
            log_handler.addFilter(InterceptAllFilter())
        self.run_load_density_thread.start()
        self.pull_log_timer.stop()
        self.pull_log_timer.start()
        self.log_panel.clear()

    def add_text_to_log(self):
        if not locust_log_queue.empty():
            self.log_panel.append(locust_log_queue.get_nowait())
