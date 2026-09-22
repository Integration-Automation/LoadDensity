"""
Run-history viewer.

Reads the SQLite persistence store and shows persisted runs in a
QTableWidget so the operator can spot regressions over time inside the
GUI.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.utils.regression.multi_run_trend import trend_runs


_COLUMNS = (
    "run_id", "started_at", "label", "requests", "failures",
    "failure_rate", "p50_ms", "p95_ms", "p99_ms",
)


class RunHistoryPanel(QWidget):
    """Tabular view of the most recent persisted runs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db_path: Optional[str] = None

        self._table = QTableWidget(0, len(_COLUMNS), self)
        self._table.setHorizontalHeaderLabels(list(_COLUMNS))
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)

        open_button = QPushButton(language_wrapper.language_word_dict.get("history_open_db"))
        open_button.clicked.connect(self._open_db)
        refresh_button = QPushButton(language_wrapper.language_word_dict.get("history_refresh"))
        refresh_button.clicked.connect(self.refresh)
        controls = QHBoxLayout()
        controls.addWidget(open_button)
        controls.addWidget(refresh_button)

        layout = QVBoxLayout()
        layout.addLayout(controls)
        layout.addWidget(self._table)
        self.setLayout(layout)

    def _open_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open LoadDensity SQLite DB", "", "SQLite (*.db *.sqlite *.sqlite3)",
        )
        if path:
            self._db_path = path
            self.refresh()

    def refresh(self) -> None:
        if not self._db_path:
            return
        trend = trend_runs(self._db_path, limit=50)
        rows = trend.get("per_run") or []
        self._table.setRowCount(len(rows))
        for row_index, run in enumerate(rows):
            for col_index, column in enumerate(_COLUMNS):
                value = run.get(column, "")
                if isinstance(value, float):
                    text = f"{value:.2f}"
                else:
                    text = str(value)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self._table.setItem(row_index, col_index, item)
