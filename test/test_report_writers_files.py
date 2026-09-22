"""Real tests for the file-based report writers (progress.md #1): Excel, histogram and PDF.

Each output is opened with an independent reader (openpyxl, the PNG signature, pypdf) rather than
only checked for existence. Tests skip when their optional reader or renderer is not installed.
"""
import pytest

from je_load_density.utils.generate_report.generate_excel_report import _column_ref, generate_excel_report
from je_load_density.utils.test_record.test_record_class import test_record_instance

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(autouse=True)
def _records(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    test_record_instance.clear_records()
    test_record_instance.test_record_list.extend([
        {"Method": "GET", "name": "/ok", "test_url": "http://h/ok", "status_code": "200",
         "response_time_ms": 12.5, "response_length": 5, "error": None},
        {"Method": "GET", "name": "/中文 & <tag>", "test_url": "http://h/x", "status_code": "200",
         "response_time_ms": 30.0, "response_length": 7, "error": None},
    ])
    test_record_instance.error_record_list.append(
        {"Method": "POST", "name": "/boom", "test_url": "http://h/boom", "status_code": "500",
         "response_time_ms": float("nan"), "response_length": 0, "error": "bad\x1b[31m byte\x00"})
    yield
    test_record_instance.clear_records()


@pytest.mark.parametrize("index, ref", [(0, "A"), (25, "Z"), (26, "AA"), (701, "ZZ"), (702, "AAA")])
def test_column_refs(index, ref):
    assert _column_ref(index) == ref


def test_excel_opens_in_openpyxl_with_every_record(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    generate_excel_report("records")
    sheet = openpyxl.load_workbook(tmp_path / "records.xlsx").active
    rows = [[cell.value for cell in row] for row in sheet.iter_rows()]
    assert rows[0][:3] == ["outcome", "Method", "name"]
    assert [row[0] for row in rows[1:]] == ["success", "success", "failure"]
    assert rows[1][5] == 12.5  # numbers stay numeric
    assert rows[2][2] == "/中文 & <tag>"  # escaped, then read back intact
    assert rows[3][7] == "bad[31m byte"  # control characters dropped, the rest kept
    assert rows[3][5] == "nan"  # a non-finite number is written as text, not as an invalid <v>


def test_histogram_writes_two_pngs(tmp_path):
    pytest.importorskip("matplotlib")
    from je_load_density.utils.generate_report.generate_histogram_report import generate_histogram_report

    paths = generate_histogram_report("latency", bins=5)
    for key in ("histogram", "cdf"):
        with open(paths[key], "rb") as handle:
            assert handle.read(8) == PNG_SIGNATURE


def test_histogram_refuses_an_empty_run():
    pytest.importorskip("matplotlib")
    from je_load_density.utils.generate_report.generate_histogram_report import (
        HistogramDependencyError,
        generate_histogram_report,
    )

    test_record_instance.clear_records()
    with pytest.raises(HistogramDependencyError, match="no records"):
        generate_histogram_report("empty")


def test_pdf_shows_a_title_with_markup_characters(tmp_path):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")
    from je_load_density.utils.generate_report.generate_pdf_report import generate_pdf_report

    summary = {"totals": {"requests": 3, "failures": 1, "failure_rate": 1 / 3},
               "latency_overall": {"p50_ms": 12.5, "p95_ms": 30.0, "p99_ms": 30.0}}
    generate_pdf_report("summary", summary=summary, title="Nightly A&B <main>")
    text = pypdf.PdfReader(tmp_path / "summary.pdf").pages[0].extract_text()
    assert "Nightly A&B <main>" in text
    assert "Requests" in text and "33.33%" in text
