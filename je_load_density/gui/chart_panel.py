"""
Live RPS / latency chart widget.

Drop into the existing PySide6 GUI alongside ``StatsPanel``. Uses
``QtCharts`` (ships with PySide6) so no extra dependency.
"""

import time
from collections import deque
from typing import Deque, Tuple

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from je_load_density.utils.test_record.test_record_class import test_record_instance


_HISTORY_SECONDS = 120


def _percentile(values, pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(pct / 100.0 * (len(ordered) - 1)))))
    return float(ordered[index])


class LiveChartPanel(QWidget):
    """Two-series line chart (RPS + p95 latency)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._buffer: Deque[Tuple[float, int, float]] = deque(maxlen=_HISTORY_SECONDS)
        self._last_count = 0
        self._start_ts = time.monotonic()

        self._rps_series = QLineSeries()
        self._rps_series.setName("RPS")
        self._latency_series = QLineSeries()
        self._latency_series.setName("p95 ms")

        chart = QChart()
        chart.addSeries(self._rps_series)
        chart.addSeries(self._latency_series)
        chart.setTitle("LoadDensity live")
        chart.legend().setAlignment(Qt.AlignBottom)

        axis_x = QValueAxis()
        axis_x.setTitleText("seconds")
        axis_x.setRange(0, _HISTORY_SECONDS)
        chart.addAxis(axis_x, Qt.AlignBottom)
        self._rps_series.attachAxis(axis_x)
        self._latency_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("value")
        axis_y.setRange(0, 100)
        chart.addAxis(axis_y, Qt.AlignLeft)
        self._rps_series.attachAxis(axis_y)
        self._latency_series.attachAxis(axis_y)

        self._chart_view = QChartView(chart)
        self._chart_view.setRenderHint(QPainter.Antialiasing)

        layout = QVBoxLayout()
        layout.addWidget(self._chart_view)
        self.setLayout(layout)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def refresh(self) -> None:
        records = (
            list(test_record_instance.test_record_list)
            + list(test_record_instance.error_record_list)
        )
        total = len(records)
        delta = max(total - self._last_count, 0)
        self._last_count = total

        latencies = [
            float(record.get("response_time_ms"))
            for record in records[-200:]
            if record.get("response_time_ms") is not None
        ]
        p95 = _percentile(latencies, 95)
        now = time.monotonic() - self._start_ts
        self._buffer.append((now, delta, p95))

        self._rps_series.clear()
        self._latency_series.clear()
        for sample in self._buffer:
            self._rps_series.append(QPointF(sample[0], sample[1]))
            self._latency_series.append(QPointF(sample[0], sample[2]))
