import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from je_load_density.gui import chart_panel  # noqa: E402
from je_load_density.utils.test_record.test_record_class import test_record_instance  # noqa: E402


@pytest.fixture
def panel():
    app = QApplication.instance() or QApplication([])
    widget = chart_panel.LiveChartPanel()
    widget._timer.stop()
    test_record_instance.clear_records()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()
    test_record_instance.clear_records()


def test_qt_bands_include_failed_samples_and_do_not_connect_latency_gaps(panel, monkeypatch):
    panel.reset_history(start_time=0)
    monkeypatch.setattr(chart_panel.time, "time", lambda: 3.0)
    test_record_instance.test_record_list.extend([
        {"start_time": 0.1, "response_time_ms": 10}, {"start_time": 0.2, "response_time_ms": 30}])
    test_record_instance.error_record_list.append({"start_time": 2.1, "response_time_ms": 80})
    panel.refresh()
    assert panel._rps_series.count() == 3
    assert panel._rps_series.at(1).y() == 0
    assert len(panel._latency_lines) == 2
    assert [line.at(0).y() for line in panel._latency_lines] == [10, 80]
    assert len(panel._band_series) == 4
    assert panel._band_series[0].upperSeries().at(0).y() == 30
    assert panel._rps_chart is not panel._latency_chart


def test_qt_history_and_visible_axes_follow_a_long_run(panel, monkeypatch):
    panel.reset_history(start_time=0)
    monkeypatch.setattr(chart_panel.time, "time", lambda: 1000.0)
    test_record_instance.test_record_list.append({"start_time": 999.1, "response_time_ms": 20000})
    panel.refresh()
    assert panel._rps_series.count() == 120
    assert panel._latency_axis_y.max() >= 20000
    assert panel._latency_axis_x.min() >= 880
