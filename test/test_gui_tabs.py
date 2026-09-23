"""The live chart and run-history panels are reachable from the main widget (progress.md #7).

Both panels shipped in 2026-05 but nothing constructed them. They now sit in a tab bar with the log.
The module skips when the optional ``gui`` extra (PySide6) is not installed.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from je_load_density.gui.chart_panel import LiveChartPanel  # noqa: E402
from je_load_density.gui.language_wrapper.english import english_word_dict  # noqa: E402
from je_load_density.gui.language_wrapper.japanese import japanese_word_dict  # noqa: E402
from je_load_density.gui.language_wrapper.korean import korean_word_dict  # noqa: E402
from je_load_density.gui.language_wrapper.traditional_chinese import traditional_chinese_word_dict  # noqa: E402
from je_load_density.gui.main_widget import LoadDensityWidget  # noqa: E402
from je_load_density.gui.run_history_panel import RunHistoryPanel  # noqa: E402


def test_widget_shows_log_chart_and_history_tabs(qtbot):
    widget = LoadDensityWidget()
    qtbot.addWidget(widget)
    pages = [widget.tabs.widget(index) for index in range(widget.tabs.count())]
    assert pages[0] is widget.log_panel
    assert isinstance(pages[1], LiveChartPanel)
    assert isinstance(pages[2], RunHistoryPanel)
    assert [widget.tabs.tabText(index) for index in range(3)] == ["Log", "Live Chart", "Run History"]


def test_chart_refresh_appends_one_sample(qtbot):
    panel = LiveChartPanel()
    qtbot.addWidget(panel)
    before = panel._rps_series.count()
    panel.refresh()
    assert panel._rps_series.count() == before + 1


def test_history_refresh_without_a_database_is_a_no_op(qtbot):
    panel = RunHistoryPanel()
    qtbot.addWidget(panel)
    panel.refresh()
    assert panel._table.rowCount() == 0


def test_every_language_has_the_same_keys():
    keys = set(english_word_dict)
    for other in (traditional_chinese_word_dict, japanese_word_dict, korean_word_dict):
        assert set(other) == keys
