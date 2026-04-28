import statistics
from typing import List

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.utils.test_record.test_record_class import test_record_instance


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = rank - lower
    return float(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction)


class StatsPanel(QWidget):
    """
    即時統計面板：定時讀取 test_record_instance 並顯示彙整數據。
    Live stats panel that polls test_record_instance and renders
    totals plus latency percentiles.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        words = language_wrapper.language_word_dict
        self.totals_label = QLabel()
        self.latency_label = QLabel()
        self.failures_label = QLabel()

        group = QGroupBox(words.get("stats_panel", "Live Stats"))
        group_layout = QVBoxLayout()
        group_layout.addWidget(self.totals_label)
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
