"""Under TestPioneer a report asked for under a relative name goes below ``TEST_PIONEER_ARTIFACT_DIR``."""
from pathlib import Path

import pytest

from je_load_density.utils.generate_report.generate_allure_report import generate_allure_report
from je_load_density.utils.generate_report.generate_cost_report import generate_cost_report
from je_load_density.utils.generate_report.generate_csv_report import generate_csv_report
from je_load_density.utils.generate_report.generate_cyclonedx_report import generate_cyclonedx_report
from je_load_density.utils.generate_report.generate_excel_report import generate_excel_report
from je_load_density.utils.generate_report.generate_html_report import generate_html_report
from je_load_density.utils.generate_report.generate_json_report import generate_json_report
from je_load_density.utils.generate_report.generate_junit_report import generate_junit_report
from je_load_density.utils.generate_report.generate_sarif_report import generate_sarif_report
from je_load_density.utils.generate_report.generate_service_map import generate_service_map
from je_load_density.utils.generate_report.generate_summary_report import generate_summary_report
from je_load_density.utils.generate_report.generate_xml_report import generate_xml_report
from je_load_density.utils.generate_report.report_path import ARTIFACT_DIR_VARIABLE, report_path
from je_load_density.utils.test_record.test_record_class import test_record_instance


@pytest.fixture(autouse=True)
def _records():
    test_record_instance.clear_records()
    test_record_instance.test_record_list.append(
        {"Method": "GET", "name": "/ok", "test_url": "http://h/ok", "status_code": "200",
         "response_time_ms": 12.5, "response_length": 5, "error": None})
    test_record_instance.error_record_list.append(
        {"Method": "POST", "name": "/boom", "test_url": "http://h/boom", "status_code": "500",
         "response_time_ms": 30.0, "response_length": 0, "error": "boom"})
    yield
    test_record_instance.clear_records()


@pytest.fixture
def artifact_dir(tmp_path, monkeypatch):
    """A TestPioneer run: the variable is set, and the working directory is somewhere else."""
    directory = tmp_path / "artifacts" / "run-1" / "runners" / "load-runner" / "01-load"
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setenv(ARTIFACT_DIR_VARIABLE, str(directory))
    return directory


def test_a_name_is_returned_as_given_outside_testpioneer(monkeypatch):
    monkeypatch.delenv(ARTIFACT_DIR_VARIABLE, raising=False)
    assert report_path("reports/load") == "reports/load"


def test_an_empty_variable_counts_as_unset(monkeypatch):
    monkeypatch.setenv(ARTIFACT_DIR_VARIABLE, "  ")
    assert report_path("reports/load") == "reports/load"


def test_a_relative_name_goes_below_the_artifact_directory(artifact_dir):
    target = Path(report_path("reports/load_success.json"))
    assert target == artifact_dir.resolve() / "reports" / "load_success.json"
    assert target.parent.is_dir()


def test_an_absolute_name_is_left_alone(artifact_dir, tmp_path):
    name = str(tmp_path / "elsewhere" / "load.json")
    assert report_path(name) == name
    assert not artifact_dir.exists()


def test_a_name_that_leaves_the_directory_is_left_alone(artifact_dir):
    assert report_path("../outside.json") == "../outside.json"
    assert not artifact_dir.exists()


def test_a_directory_that_cannot_be_created_falls_back_to_the_name(tmp_path, monkeypatch):
    not_a_directory = tmp_path / "file"
    not_a_directory.write_text("x", encoding="utf-8")
    monkeypatch.setenv(ARTIFACT_DIR_VARIABLE, str(not_a_directory))
    assert report_path("reports/load.json") == "reports/load.json"


@pytest.mark.parametrize("generate, name, written", [
    (generate_json_report, "reports/load", ["reports/load_success.json", "reports/load_failure.json"]),
    (generate_xml_report, "reports/load", ["reports/load_success.xml", "reports/load_failure.xml"]),
    (generate_html_report, "reports/load", ["reports/load.html"]),
    (generate_junit_report, "reports/junit", ["reports/junit.xml"]),
    (generate_summary_report, "reports/summary", ["reports/summary.json"]),
    (generate_csv_report, "reports/load", ["reports/load.csv"]),
    (generate_cost_report, "reports/cost", ["reports/cost.json"]),
    (generate_cyclonedx_report, "reports/bom", ["reports/bom.cdx.json"]),
    (generate_sarif_report, "reports/load", ["reports/load.sarif.json"]),
    (generate_service_map, "reports/map", ["reports/map.json"]),
    (generate_excel_report, "reports/load", ["reports/load.xlsx"]),
], ids=["json", "xml", "html", "junit", "summary", "csv", "cost", "cyclonedx", "sarif", "service-map", "excel"])
def test_a_report_is_written_below_the_artifact_directory(artifact_dir, generate, name, written):
    generate(name)
    assert [(artifact_dir / path).is_file() for path in written] == [True] * len(written)
    # Nothing is left in the working directory, where the name used to point.
    assert not Path("reports").exists()


def test_a_generator_returns_the_path_it_wrote(artifact_dir):
    success, failure = generate_json_report("reports/load")
    assert Path(success) == artifact_dir.resolve() / "reports" / "load_success.json"
    assert Path(failure).is_file()


def test_the_allure_results_are_written_below_the_artifact_directory(artifact_dir):
    output = generate_allure_report("allure-results")
    assert Path(output) == artifact_dir.resolve() / "allure-results"
    assert any(Path(output).glob("*-result.json"))
    assert not Path("allure-results").exists()


def test_the_charts_are_written_below_the_artifact_directory(artifact_dir):
    pytest.importorskip("matplotlib")
    from je_load_density.utils.generate_report.generate_histogram_report import generate_histogram_report

    paths = generate_histogram_report("reports/latency", bins=5)
    assert Path(paths["histogram"]) == artifact_dir.resolve() / "reports" / "latency-histogram.png"
    assert Path(paths["cdf"]).is_file()


def test_the_pdf_is_written_below_the_artifact_directory(artifact_dir):
    pytest.importorskip("reportlab")
    from je_load_density.utils.generate_report.generate_pdf_report import generate_pdf_report

    generate_pdf_report("reports/load")
    assert (artifact_dir / "reports" / "load.pdf").is_file()


def test_outside_testpioneer_a_report_stays_in_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.delenv(ARTIFACT_DIR_VARIABLE, raising=False)
    monkeypatch.chdir(tmp_path)
    generate_json_report("load")
    assert (tmp_path / "load_success.json").is_file()
