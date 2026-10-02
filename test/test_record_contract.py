import json

import pytest

pytest.importorskip("je_action_core.request_context", reason="coordinated ActionCore request-record release")

from je_load_density.utils.test_record.contract import from_legacy_record, record_request
from je_load_density.utils.test_record.run_context import RunContext, get_run_context, use_run_context


def context():
    return RunContext(source="loaddensity", phase="load", engine="locust")


def test_legacy_success_maps_types_without_inventing_timestamps():
    result = from_legacy_record({"Method": "get", "test_url": "http://localhost/", "name": "home",
                                 "status_code": "200", "response_time_ms": 25, "response_length": 2},
                                context(), "passed")
    assert result["request_method"] == "GET"
    assert result["status_code"] == 200
    assert result["start_time"] is None
    assert result["end_time"] is None
    assert result["response_time_ms"] == 25.0


def test_transport_sentinel_and_missing_latency_remain_unknown():
    result = from_legacy_record({"Method": "GET", "test_url": "http://localhost/", "status_code": "0",
                                 "error": "connection refused"}, context(), "failed")
    assert result["status_code"] is None
    assert result["response_time_ms"] is None
    assert result["error"]["message"] == "connection refused"


def test_request_capture_redacts_sensitive_headers_and_retains_binary_body():
    run = context()
    with use_run_context(run):
        record_request({"Method": "GET", "test_url": "http://localhost/", "status_code": "200",
                        "response_time_ms": 25, "start_time": 100.0, "content": b"\x00\xff",
                        "headers": {"Authorization": "secret", "Content-Type": "application/json",
                                    "Set-Cookie": "session=secret"}}, "passed", capture_payload=True)
    record = json.loads(run.to_json())[0]
    assert record["end_time"] == 100.025
    assert record["content_base64"] == "AP8="
    assert record["headers"] == {"Authorization": "[REDACTED]", "Content-Type": "application/json",
                                  "Set-Cookie": "[REDACTED]"}


def test_recording_without_explicit_context_is_a_no_op():
    assert get_run_context() is None
    assert record_request({"Method": "GET"}, "passed") is None


def test_malformed_legacy_record_reports_field_location():
    with pytest.raises(ValueError, match="status_code"):
        from_legacy_record({"Method": "GET", "test_url": "http://localhost/", "status_code": "bad"},
                           context(), "passed")


def test_live_payload_capture_is_disabled_by_default():
    run = context()
    with use_run_context(run):
        record_request({"Method": "GET", "test_url": "http://localhost/", "status_code": "200",
                        "content": b"secret", "text": "secret"}, "passed")
    result = run.snapshot()[0]
    assert "content_base64" not in result
    assert "text" not in result
