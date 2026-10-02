"""Bounded latency bands and a separate request-rate chart for Qt."""

import math
import time
from itertools import chain

from PySide6.QtCharts import QAreaSeries, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.utils.test_record.window_statistics import latency_windows

_HISTORY_SECONDS = 120


def _chart(title: str, unit: str):
    chart = QChart()
    chart.setTitle(title)
    chart.legend().setAlignment(Qt.AlignBottom)
    x, y = QValueAxis(), QValueAxis()
    x.setTitleText("elapsed seconds")
    x.setRange(0, _HISTORY_SECONDS)
    y.setTitleText(unit)
    y.setRange(0, 100)
    chart.addAxis(x, Qt.AlignBottom)
    chart.addAxis(y, Qt.AlignLeft)
    view = QChartView(chart)
    view.setRenderHint(QPainter.Antialiasing)
    return chart, view, x, y


def _segments(windows):
    segment = []
    for window in windows:
        if window["p50_ms"] is None:
            if segment:
                yield segment
                segment = []
        else:
            segment.append(window)
    if segment:
        yield segment


class LiveChartPanel(QWidget):
    """p50 line and p50–p95/p95–p99 bands; gaps remain disconnected."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._latency_chart, self._chart_view, self._latency_axis_x, self._latency_axis_y = _chart(
            "Latency · p50 / p95 / p99", "milliseconds")
        self._rps_chart, self._rps_view, self._rps_axis_x, self._rps_axis_y = _chart("Throughput", "requests / second")
        self._rps_chart.legend().hide()
        self._rps_series = QLineSeries()
        self._rps_series.setName("RPS")
        self._rps_chart.addSeries(self._rps_series)
        self._rps_series.attachAxis(self._rps_axis_x)
        self._rps_series.attachAxis(self._rps_axis_y)
        self._latency_lines = []
        self._band_series = []
        self.reset_history()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._chart_view, 2)
        layout.addWidget(self._rps_view, 1)
        self._chart_view.setMinimumHeight(220)
        self._rps_view.setMinimumHeight(160)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def reset_history(self, start_time: float | None = None) -> None:
        self._start_epoch = math.floor(time.time()) if start_time is None else start_time
        self._rps_series.clear()
        self._latency_chart.removeAllSeries()
        self._latency_lines.clear()
        self._band_series.clear()

    def _add_latency(self, series) -> None:
        self._latency_chart.addSeries(series)
        series.attachAxis(self._latency_axis_x)
        series.attachAxis(self._latency_axis_y)

    def _line(self, segment, key: str):
        series = QLineSeries()
        series.replace([QPointF(item["start_time"] - self._start_epoch, item[key]) for item in segment])
        return series

    def _band(self, segment, lower: str, upper: str, color: str):
        low, high = self._line(segment, lower), self._line(segment, upper)
        area = QAreaSeries(high, low)
        # Area boundaries stay caller-owned; parent them explicitly for refresh cleanup.
        low.setParent(area)
        high.setParent(area)
        area.setName(f"{lower.split('_')[0]}–{upper.split('_')[0]}")
        area.setColor(QColor(color))
        area.setBorderColor(QColor("transparent"))
        self._add_latency(area)
        self._band_series.append(area)

    def _render_latency(self, windows) -> None:
        self._latency_chart.removeAllSeries()
        self._latency_lines.clear()
        self._band_series.clear()
        for index, segment in enumerate(_segments(windows)):
            self._band(segment, "p50_ms", "p95_ms", "#664fc3f7")
            self._band(segment, "p95_ms", "p99_ms", "#33a78bfa")
            line = self._line(segment, "p50_ms")
            line.setName("p50")
            line.setColor(QColor("#1591d0"))
            line.setPointsVisible(True)
            self._add_latency(line)
            self._latency_lines.append(line)
            if index:
                for series in (line, *self._band_series[-2:]):
                    for marker in self._latency_chart.legend().markers(series):
                        marker.setVisible(False)

    def refresh(self) -> None:
        now = max(time.time(), self._start_epoch)
        records = chain(test_record_instance.test_record_list, test_record_instance.error_record_list)
        windows = latency_windows(records, start=self._start_epoch, end=now, max_buckets=_HISTORY_SECONDS)
        self._rps_series.replace([QPointF(item["start_time"] - self._start_epoch, item["rps"]) for item in windows])
        self._render_latency(windows)
        left = windows[0]["start_time"] - self._start_epoch if windows else 0
        right = max(left + 1, now - self._start_epoch)
        for axis in (self._latency_axis_x, self._rps_axis_x):
            axis.setRange(left, right)
        self._latency_axis_y.setRange(0, max(1, max((item["p99_ms"] or 0 for item in windows), default=0) * 1.15))
        self._rps_axis_y.setRange(0, max(1, max((item["rps"] for item in windows), default=0) * 1.15))
