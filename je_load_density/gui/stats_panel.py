import statistics
from typing import List

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.utils.test_record.window_statistics import percentile


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    return percentile(values, pct) or 0.0


class StatsPanel(QWidget):
    """
    即時統計面板：定時讀取 test_record_instance 並顯示彙整數據。
    Live stats panel that polls test_record_instance and renders
    totals plus latency percentiles.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        words = language_wrapper.language_word_dict
        self.totals_label = QLabel()
        self.latency_label = QLabel()
        self.failures_label = QLabel()
        self.capacity_label = QLabel()

        group = QGroupBox(words.get("stats_panel", "Live Stats"))
        group_layout = QVBoxLayout()
        header = QHBoxLayout()
        header.addWidget(self.totals_label)
        header.addStretch()
        header.addWidget(self.capacity_label)
        group_layout.addLayout(header)
        group_layout.addWidget(self.latency_label)
        group_layout.addWidget(self.failures_label)
        group.setLayout(group_layout)

        layout.addWidget(group)
        self.setLayout(layout)

        self._last_total = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def set_snapshot(self, summary: dict) -> None:
        """Render cumulative child totals independently of the bounded request table."""
        self._timer.stop()
        words = language_wrapper.language_word_dict
        self.totals_label.setText(f"{words['stats_total']}: {summary.get('requests', 0)}    "
                                  f"{words['stats_rate']}: {summary.get('rps', 0):.1f}/s")
        percentiles = "    ".join(f"p{pct}: {summary.get(f'p{pct}_ms') or 0:.1f} ms" for pct in (50, 95, 99))
        self.latency_label.setText(percentiles)
        self.failures_label.setText(f"{words['stats_failures']}: {summary.get('failures', 0)}    "
                                    f"{words['failure_rate']}: {summary.get('failure_rate', 0):.1%}")
        self.capacity_label.setText(f"{words['user_count']}: {summary.get('users', 0)}")

    def refresh(self) -> None:
        success_records = test_record_instance.test_record_list
        failure_records = test_record_instance.error_record_list
        total = len(success_records) + len(failure_records)
        delta = max(total - self._last_total, 0)
        self._last_total = total

        latencies = [
            float(record.get("response_time_ms"))
            for record in (*success_records, *failure_records)
            if record.get("response_time_ms") is not None
        ]
        avg_ms = statistics.fmean(latencies) if latencies else 0.0
        p95_ms = _percentile(latencies, 95)

        words = language_wrapper.language_word_dict
        self.totals_label.setText(
            f"{words.get('stats_total', 'Total')}: {total}    "
            f"{words.get('stats_rate', 'Rate')}: {delta}/s"
        )
        self.latency_label.setText(
            f"{words.get('stats_avg_ms', 'Avg')}: {avg_ms:.1f} ms    "
            f"{words.get('stats_p95_ms', 'p95')}: {p95_ms:.1f} ms"
        )
        self.failures_label.setText(
            f"{words.get('stats_failures', 'Failures')}: {len(failure_records)}"
        )
