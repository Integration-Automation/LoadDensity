"""Desktop settings and run inspection; all view mutations happen in Qt slots."""

from urllib.parse import urlsplit

from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QIntValidator, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from je_load_density.gui.chart_panel import LiveChartPanel
from je_load_density.gui.dark_style import apply_dark_style
from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.gui.load_density_gui_thread import LoadDensityGUIThread
from je_load_density.gui.log_to_ui_filter import log_message_queue
from je_load_density.gui.run_history_panel import RunHistoryPanel
from je_load_density.gui.stats_panel import StatsPanel
from je_load_density.utils.test_record.test_record_class import test_record_instance


class LoadDensityWidget(QWidget):
    """Keep settings left and state, metrics, charts and inspectable results right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        apply_dark_style(self)
        self.words = language_wrapper.language_word_dict
        self.run_state = "idle"
        self.run_load_density_thread = None
        self.last_summary = {}
        self._settings = self._build_settings()
        inspection = self._build_inspection()
        splitter = QSplitter()
        splitter.addWidget(self._settings)
        splitter.addWidget(inspection)
        splitter.setStretchFactor(1, 1)
        layout = QHBoxLayout(self)
        layout.addWidget(splitter)
        self.pull_log_timer = QTimer(self)
        self.pull_log_timer.setInterval(100)
        self.pull_log_timer.timeout.connect(self.add_text_to_log)
        self._set_state("idle")

    def _build_settings(self) -> QWidget:
        settings = QGroupBox(self.words["settings"])
        form = QFormLayout(settings)
        self.action_file_input = QLineEdit()
        browse = QPushButton(self.words["browse"])
        browse.clicked.connect(self._browse_action)
        action_row = QHBoxLayout()
        action_row.addWidget(self.action_file_input)
        action_row.addWidget(browse)
        form.addRow(self.words["action_file"], action_row)
        self.url_input = QLineEdit("http://localhost:8080/")
        self.engine_combobox = QComboBox()
        self.engine_combobox.addItems(["Locust", "asyncio"])
        self.test_time_input = QLineEdit("10")
        self.user_count_input = QLineEdit("1")
        self.spawn_rate_input = QLineEdit("1")
        for field in (self.test_time_input, self.user_count_input, self.spawn_rate_input):
            field.setValidator(QIntValidator(1, 2147483647, field))
        self.method_combobox = QComboBox()
        self.method_combobox.addItems([self.words[key] for key in
                                       ("get", "post", "put", "patch", "delete", "head", "options")])
        for key, field in (("url", self.url_input), ("engine", self.engine_combobox),
                           ("user_count", self.user_count_input), ("spawn_rate", self.spawn_rate_input),
                           ("test_time", self.test_time_input), ("test_method", self.method_combobox)):
            form.addRow(self.words[key], field)
        settings.setMinimumWidth(270)
        return settings

    def _build_inspection(self) -> QWidget:
        inspection = QWidget()
        layout = QVBoxLayout(inspection)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        self.state_label = QLabel()
        self.start_button = QPushButton(self.words["start_button"])
        self.stop_button = QPushButton(self.words["stop_button"])
        self.start_button.clicked.connect(self.run_load_density)
        self.stop_button.clicked.connect(self.stop_load_density)
        for widget in (self.state_label, self.start_button, self.stop_button):
            controls.addWidget(widget)
        layout.addLayout(controls)
        self.stats_panel = StatsPanel()
        self.stats_panel.set_snapshot({})
        layout.addWidget(self.stats_panel)
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.document().setMaximumBlockCount(500)
        self.chart_panel = LiveChartPanel()
        self.chart_panel._chart_view.setMinimumHeight(260)
        self.chart_panel._rps_view.setMinimumHeight(220)
        self.chart_panel.layout().setStretch(0, 1)
        self.chart_panel.layout().setStretch(1, 1)
        self.history_panel = RunHistoryPanel()
        self.tabs = QTabWidget()
        for widget, key in ((self.log_panel, "tab_log"), (self.chart_panel, "tab_chart"),
                            (self.history_panel, "tab_history")):
            self.tabs.addTab(widget, self.words[key])
        self.tabs.setCurrentIndex(1)
        layout.addWidget(self.tabs, 2)
        layout.addWidget(QLabel(self.words["results"]))
        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels([self.words["request"], self.words["latency"],
                                                     self.words["result"]])
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setMinimumHeight(110)
        self.results_table.setMaximumHeight(220)
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.results_table, 1)
        return inspection

    def _browse_action(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.words["action_file"], "", "Actions (*.json *.yaml *.yml)")
        if path:
            self.action_file_input.setText(path)

    def _configuration(self) -> dict:
        users, spawn, duration = (int(field.text()) for field in
                                  (self.user_count_input, self.spawn_rate_input, self.test_time_input))
        if min(users, spawn, duration) <= 0:
            raise ValueError("Positive load settings required")
        action_file = self.action_file_input.text().strip()
        target = self.url_input.text().strip()
        if not action_file and (urlsplit(target).scheme not in {"http", "https"} or not urlsplit(target).hostname):
            raise ValueError("HTTP target required")
        return {"request_url": target, "user_count": users, "spawn_rate": spawn, "test_duration": duration,
                "http_method": self.method_combobox.currentText().lower(),
                "engine": self.engine_combobox.currentText().lower(), "action_file": action_file}

    @Slot()
    def run_load_density(self) -> None:
        """Reject duplicate starts and retain prior results until new settings validate."""
        if self.run_state in {"running", "stopping"}:
            return
        if self.run_load_density_thread is not None and self.run_load_density_thread.isRunning():
            return
        try:
            config = self._configuration()
        except ValueError:
            self._append_log(self.words["invalid_input"])
            return
        worker = LoadDensityGUIThread(**config)
        self.run_load_density_thread = worker
        worker.state_changed.connect(self._worker_state)
        worker.snapshot_ready.connect(self._snapshot)
        worker.log_message.connect(self._append_log)
        worker.completed.connect(self._completed)
        self.log_panel.clear()
        self.last_summary = {}
        self.stats_panel.set_snapshot({})
        self.results_table.setRowCount(0)
        test_record_instance.clear_records()
        self.chart_panel.reset_history()
        self.chart_panel._timer.start()
        self._set_state("running")
        self._append_log(self.words["running"])
        worker.start()

    @Slot()
    def stop_load_density(self) -> None:
        """Show stopping immediately and ask the isolated engine to cancel cooperatively."""
        if self.run_state != "running":
            return
        self._set_state("stopping")
        self.run_load_density_thread.request_stop()

    def _set_state(self, state: str) -> None:
        self.run_state = state
        self.state_label.setText(self.words.get(state, state))
        active = state in {"running", "stopping"}
        self.start_button.setEnabled(not active)
        self.stop_button.setEnabled(state == "running")
        self._settings.setEnabled(not active)

    @Slot(str)
    def _worker_state(self, state: str) -> None:
        if self.run_state != "stopping":
            self._set_state(state)

    @Slot(dict)
    def _snapshot(self, snapshot: dict) -> None:
        self.last_summary = snapshot["summary"]
        self.stats_panel.set_snapshot(self.last_summary)
        records = snapshot.get("records", [])[-200:]
        test_record_instance.test_record_list[:] = [row for row in records if not row.get("failed")]
        test_record_instance.error_record_list[:] = [row for row in records if row.get("failed")]
        self.results_table.setRowCount(len(records))
        for index, record in enumerate(records):
            latency = record.get("response_time_ms")
            values = (record.get("name", "request"), f"{latency:.1f}" if latency is not None else "",
                      self.words["failed"] if record.get("failed") else self.words["success"])
            for column, value in enumerate(values):
                self.results_table.setItem(index, column, QTableWidgetItem(str(value)))
        self.chart_panel.set_snapshot(snapshot)

    @Slot(dict)
    def _completed(self, result: dict) -> None:
        self.chart_panel._timer.stop()
        self.last_summary = result.get("summary", self.last_summary)
        self.stats_panel.set_snapshot(self.last_summary)
        self._set_state(result["state"])
        self._append_log(self.words.get(result["state"], result["state"]))

    @Slot(str)
    def _append_log(self, message: str) -> None:
        cursor = self.log_panel.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(str(message)[:1200] + "\n")
        self.log_panel.setTextCursor(cursor)

    def add_text_to_log(self) -> None:
        """Retain the legacy queued logging entrypoint with a bounded per tick drain."""
        for _ in range(100):
            if log_message_queue.empty():
                break
            self._append_log(log_message_queue.get_nowait())

    def shutdown(self) -> bool:
        """Stop timers and cancel/join the worker before the widget is destroyed."""
        self.pull_log_timer.stop()
        self.stats_panel._timer.stop()
        self.chart_panel._timer.stop()
        if self.run_load_density_thread is None:
            return True
        return self.run_load_density_thread.shutdown()

    def closeEvent(self, event) -> None:
        """Allow destruction only after the execution thread has joined."""
        if self.shutdown():
            event.accept()
        else:
            event.ignore()
