"""Real tests for the 2026-05 report generators (progress.md #1) and the request order they rely on."""
import json
from types import SimpleNamespace

import pytest

from je_load_density.utils.generate_report.generate_allure_report import generate_allure_report
from je_load_density.utils.generate_report.generate_cost_report import estimate_run_cost, generate_cost_report
from je_load_density.utils.generate_report.generate_cyclonedx_report import generate_cyclonedx_report
from je_load_density.utils.generate_report.generate_sarif_report import generate_sarif_report
from je_load_density.utils.generate_report.generate_service_map import build_service_map
from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.wrapper.event.request_hook import request_hook


@pytest.fixture(autouse=True)
def _clean_records(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # every generator writes relative to the cwd
    test_record_instance.clear_records()
    yield
    test_record_instance.clear_records()


def _ok(name, start):
    return {"name": name, "Method": "GET", "status_code": "200", "response_time_ms": 10.0,
            "response_length": 2, "error": None, "start_time": start}


def _fail(name, start):
    return {"name": name, "Method": "POST", "status_code": "500", "response_time_ms": 40.0,
            "response_length": 0, "error": "HTTP 500", "start_time": start}


def test_hook_records_the_request_start_time():
    response = SimpleNamespace(status_code=200, text="ok", content=b"ok", headers={})
    request_hook(1_700_000_000.5, "http://h/a", "GET", "/a", {}, response, None, 2, 12.0)
    request_hook(1_700_000_001.0, "http://h/b", "GET", "/b", {}, response, RuntimeError("boom"), 0, 30.0)
    assert test_record_instance.test_record_list[0]["start_time"] == 1_700_000_000.5
    assert test_record_instance.error_record_list[0]["start_time"] == 1_700_000_001.0


def test_service_map_follows_request_order_across_successes_and_failures():
    # Request order: /login (ok) -> /cart (fails) -> /checkout (ok).
    test_record_instance.test_record_list.extend([_ok("/login", 1.0), _ok("/checkout", 3.0)])
    test_record_instance.error_record_list.append(_fail("/cart", 2.0))
    edges = {(edge["source"], edge["target"]) for edge in build_service_map()["edges"]}
    assert edges == {("/login", "/cart"), ("/cart", "/checkout")}


def test_service_map_min_weight_drops_rare_edges():
    test_record_instance.test_record_list.extend(
        [_ok("/a", 1.0), _ok("/b", 2.0), _ok("/a", 3.0), _ok("/b", 4.0), _ok("/c", 5.0)])
    edges = build_service_map(min_weight=2)["edges"]
    assert edges == [{"source": "/a", "target": "/b", "weight": 2}]


def test_cost_breakdown_arithmetic():
    cost = estimate_run_cost(duration_seconds=1800, workers=4, hourly_rate_usd=0.5,
                             egress_gb=10, egress_rate_usd_per_gb=0.1, extra_costs_usd={"logs": 0.25})
    assert cost["compute_usd"] == pytest.approx(1.0)
    assert cost["egress_usd"] == pytest.approx(1.0)
    assert cost["total_usd"] == pytest.approx(2.25)


def test_cost_report_is_written_as_json(tmp_path):
    path = generate_cost_report("run-cost", duration_seconds=3600, workers=2, hourly_rate_usd=1.0)
    assert json.loads((tmp_path / "run-cost.json").read_text(encoding="utf-8"))["total_usd"] == 2.0
    assert path.endswith("run-cost.json")


def test_sarif_lists_each_failure(tmp_path):
    test_record_instance.error_record_list.append(_fail("/cart", 2.0))
    generate_sarif_report("scan", extra_records=[{"name": "/extra", "error": "timeout"}])
    document = json.loads((tmp_path / "scan.sarif.json").read_text(encoding="utf-8"))
    assert document["version"] == "2.1.0"
    messages = [result["message"]["text"] for result in document["runs"][0]["results"]]
    assert messages == ["/cart: HTTP 500", "/extra: timeout"]


def test_allure_uses_the_recorded_start_time(tmp_path):
    test_record_instance.test_record_list.append(_ok("/a", 1_700_000_000.0))
    test_record_instance.error_record_list.append(_fail("/b", 1_700_000_001.0))
    generate_allure_report(str(tmp_path / "allure"), label="nightly")
    results = sorted(
        (json.loads(path.read_text(encoding="utf-8")) for path in (tmp_path / "allure").glob("*-result.json")),
        key=lambda body: body["start"])
    assert [(body["name"], body["status"]) for body in results] == [("/a", "passed"), ("/b", "failed")]
    assert results[0]["start"] == 1_700_000_000_000
    assert results[0]["stop"] - results[0]["start"] == 10
    assert (tmp_path / "allure" / "environment.properties").read_text(encoding="utf-8") == "label=nightly\n"


def test_cyclonedx_lists_installed_distributions(tmp_path):
    generate_cyclonedx_report("sbom")
    document = json.loads((tmp_path / "sbom.cdx.json").read_text(encoding="utf-8"))
    assert document["bomFormat"] == "CycloneDX"
    names = {component["name"].lower() for component in document["components"]}
    assert "locust" in names
    assert all(component["purl"].startswith("pkg:pypi/") for component in document["components"])
