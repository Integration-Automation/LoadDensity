import json
import os

import pytest

from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.utils.generate_report.generate_html_report import generate_html, generate_html_report
from je_load_density.utils.generate_report.generate_json_report import generate_json, generate_json_report
from je_load_density.utils.generate_report.generate_xml_report import generate_xml, generate_xml_report
from je_load_density.utils.exception.exceptions import (
    LoadDensityHTMLException,
    LoadDensityGenerateJsonReportException,
)

_SUCCESS_RECORD = {
    "Method": "GET",
    "test_url": "http://example.com/get",
    "name": "/get",
    "status_code": "200",
    "text": "OK",
    "content": b"OK",
    "headers": "{'Content-Type': 'application/json'}",
    "error": None,
}

_FAILURE_RECORD = {
    "Method": "POST",
    "test_url": "http://example.com/post",
    "name": "/post",
    "status_code": "500",
    "error": "Internal Server Error",
}


@pytest.fixture(autouse=True)
def _clean_records():
    """Clear global test records before and after each test."""
    test_record_instance.clear_records()
    yield
    test_record_instance.clear_records()


class TestGenerateHtml:

    def test_no_data_raises(self):
        with pytest.raises(LoadDensityHTMLException):
            generate_html()

    def test_success_records(self):
        test_record_instance.test_record_list.append(_SUCCESS_RECORD)
        success_list, failure_list = generate_html()
        assert len(success_list) == 1
        assert len(failure_list) == 0
        assert "200" in success_list[0]
        assert "example.com" in success_list[0]

    def test_failure_records(self):
        test_record_instance.error_record_list.append(_FAILURE_RECORD)
        success_list, failure_list = generate_html()
        assert len(success_list) == 0
        assert len(failure_list) == 1
        assert "Internal Server Error" in failure_list[0]

    def test_html_report_file(self, tmp_path):
        test_record_instance.test_record_list.append(_SUCCESS_RECORD)
        report_path = str(tmp_path / "report")
        result = generate_html_report(html_name=report_path)
        assert result == f"{report_path}.html"
        assert os.path.isfile(result)
        with open(result, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "200" in content


class TestGenerateJson:

    def test_no_data_raises(self):
        with pytest.raises(LoadDensityGenerateJsonReportException):
            generate_json()

    def test_success_records(self):
        test_record_instance.test_record_list.append(_SUCCESS_RECORD)
        success_dict, failure_dict = generate_json()
        assert "Success_Test1" in success_dict
        assert success_dict["Success_Test1"]["Method"] == "GET"
        assert len(failure_dict) == 0

    def test_failure_records(self):
        test_record_instance.error_record_list.append(_FAILURE_RECORD)
        success_dict, failure_dict = generate_json()
        assert len(success_dict) == 0
        assert "Failure_Test1" in failure_dict

    def test_json_report_files(self, tmp_path):
        test_record_instance.test_record_list.append(_SUCCESS_RECORD)
        report_path = str(tmp_path / "report")
        success_path, failure_path = generate_json_report(json_file_name=report_path)
        assert os.path.isfile(success_path)
        assert os.path.isfile(failure_path)
        with open(success_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "Success_Test1" in data


class TestGenerateXml:

    def test_no_data_raises(self):
        with pytest.raises(LoadDensityGenerateJsonReportException):
            generate_xml()

    def test_success_xml(self):
        test_record_instance.test_record_list.append(_SUCCESS_RECORD)
        success_xml, failure_xml = generate_xml()
        assert "<Method>GET</Method>" in success_xml
        assert "<xml_data" in success_xml

    def test_xml_report_files(self, tmp_path):
        test_record_instance.test_record_list.append(_SUCCESS_RECORD)
        report_path = str(tmp_path / "report")
        success_path, failure_path = generate_xml_report(xml_file_name=report_path)
        assert os.path.isfile(success_path)
        assert os.path.isfile(failure_path)
        with open(success_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "GET" in content
