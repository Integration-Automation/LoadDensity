import math

import pytest

from je_load_density.utils.generate_report.generate_chart_report import (
    ChartDependencyError,
    generate_chart_report,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance


def _push_records(latencies):
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    for i, latency in enumerate(latencies):
        test_record_instance.test_record_list.append({
            "Method": "GET", "test_url": "/x", "name": "/x",
            "status_code": "200", "response_time_ms": latency,
            "ts": float(i),
        })


def test_generate_chart_report_writes_png(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    monkeypatch.chdir(tmp_path)
    _push_records([10.0, 20.0, 30.0])
    out = generate_chart_report("charts")
    assert out["latency"].endswith("charts-latency.png")
    assert out["rps"].endswith("charts-rps.png")


def test_generate_chart_report_raises_when_no_records(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    monkeypatch.chdir(tmp_path)
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    with pytest.raises(ChartDependencyError):
        generate_chart_report("charts")


def test_latency_bands_include_failures_and_leave_empty_seconds_disconnected(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    from matplotlib.axes import Axes

    _push_records([10])
    test_record_instance.error_record_list.append({"start_time": 2.1, "response_time_ms": 80, "error": "500"})
    bands = []
    original = Axes.fill_between

    def capture(axis, x, low, high, **kwargs):
        bands.append((list(x), list(low), list(high)))
        return original(axis, x, low, high, **kwargs)

    monkeypatch.setattr(Axes, "fill_between", capture)
    paths = generate_chart_report(str(tmp_path / "bands"))
    assert len(bands) == 2
    assert bands[0][1][0] == 10
    assert bands[0][1][2] == 80
    assert math.isnan(bands[0][1][1])  # NaN prevents connecting the empty bucket.
    for path in paths.values():
        with open(path, "rb") as image:
            assert image.read(8) == b"\x89PNG\r\n\x1a\n"
