"""The detection side of the security helpers: OWASP API checks, SSRF targets and metadata-leak
detection, and the rate-limit probe (with ``urlopen`` stubbed, so no request leaves the test).
"""
import io
import urllib.error
import urllib.request

import pytest

from je_load_density.utils.security import owasp_checks, rate_limit_probe, ssrf_checks

_ALL_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'",
}


# --- OWASP checks ----------------------------------------------------------------------------

@pytest.mark.parametrize("body", [
    {"user": {"id": 1, "password": "hunter2"}},  # parsed JSON: the field is a key
    '{"user": {"id": 1, "password": "hunter2"}}',  # raw JSON text
    [{"id": 1}, {"id": 2, "password": "x"}],
], ids=["parsed", "raw-text", "list"])
def test_excessive_data_exposure_finds_the_field(body):
    findings = owasp_checks.check_excessive_data_exposure(body, ["password", "ssn"])
    assert [finding["field"] for finding in findings] == ["password"]
    assert findings[0]["rule"] == "owasp.api3.excessive_data_exposure"


def test_excessive_data_exposure_ignores_the_word_in_a_value():
    assert owasp_checks.check_excessive_data_exposure({"hint": "reset your password"}, ["password"]) == []


def test_bola_suspect_needs_five_successful_hits_on_a_users_endpoint():
    ok = [{"status_code": 200, "name": "GET /users/{id}"}] * 5
    too_few = [{"status_code": 200, "name": "GET /users/{me}"}] * 4
    denied = [{"status_code": 403, "name": "GET /users/{x}"}] * 9
    other = [{"status_code": 200, "name": "GET /orders/{id}"}] * 9
    findings = owasp_checks.check_broken_object_level_auth(ok + too_few + denied + other)
    assert findings == [{"rule": "owasp.api1.bola_suspect", "endpoint": "GET /users/{id}", "hits": 5,
                         "severity": "info"}]


def test_security_headers_are_matched_case_insensitively():
    assert owasp_checks.check_security_headers(_ALL_HEADERS) == []
    missing = owasp_checks.check_security_headers({"x-content-type-options": "nosniff"})
    assert sorted(finding["header"] for finding in missing) == ["content-security-policy",
                                                                "strict-transport-security"]


def test_sensitive_token_leak_lists_each_token_once():
    findings = owasp_checks.check_sensitive_token_leak("Authorization: Bearer x; api_key=1; API_KEY=2")
    assert sorted(finding["token"] for finding in findings) == ["api_key", "authorization"]


def test_run_owasp_checks_combines_every_check():
    findings = owasp_checks.run_owasp_checks({"secret": "value", "note": "token rotated"}, {}, [], ["secret"])
    rules = [finding["rule"] for finding in findings]
    assert "owasp.api3.excessive_data_exposure" in rules
    assert rules.count("owasp.api8.missing_hsts") == 1
    assert {"rule": "owasp.api3.sensitive_data_in_response", "token": "token",
            "severity": "warning"} in findings


# --- SSRF --------------------------------------------------------------------------------------

def test_ssrf_tasks_copy_the_template_per_target():
    template = {"method": "get", "request_url": "https://app.test/fetch", "headers": {"X": "1"}}
    tasks = ssrf_checks.render_ssrf_tasks(template)
    targets = ssrf_checks.build_ssrf_targets()
    assert [task["request_url"] for task in tasks] == targets
    assert all(task["name"] == f"ssrf::{task['request_url']}" and task["method"] == "get" for task in tasks)
    assert template["request_url"] == "https://app.test/fetch"  # the template is not modified


@pytest.mark.parametrize("body, expected", [
    ("ami-id\ninstance-id\n", ["ami-id", "instance-id"]),
    ('{"Metadata-Flavor": "Google"}', ["Metadata-Flavor"]),
    ("hello", []),
    (None, []),
])
def test_find_metadata_leak(body, expected):
    assert ssrf_checks.find_metadata_leak(body) == expected


# --- rate-limit probe --------------------------------------------------------------------------

class _Response:
    def __init__(self, status, headers=()):
        self.status = status
        self._headers = list(headers)

    def getheaders(self):
        return self._headers

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen(statuses):
    calls = []

    def urlopen(request, timeout):
        calls.append((request.full_url, request.get_method(), timeout))
        status = statuses[len(calls) - 1]
        if status >= 400:
            raise urllib.error.HTTPError(request.full_url, status, "limited",
                                         {"Retry-After": "3", "X-RateLimit-Limit": "5", "Server": "x"},
                                         io.BytesIO())
        return _Response(status)
    return urlopen, calls


def test_probe_stops_at_the_first_throttled_request(monkeypatch):
    urlopen, calls = _fake_urlopen([200, 200, 429, 200])
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    result = rate_limit_probe.probe_rate_limit("https://api.test/x", method="POST", burst=4, timeout=1.5)
    assert result["first_throttled_at"] == 2
    assert result["throttle_headers"] == {"Retry-After": "3", "X-RateLimit-Limit": "5"}
    assert calls == [("https://api.test/x", "POST", 1.5)] * 3


def test_probe_without_throttling_reports_none(monkeypatch):
    urlopen, calls = _fake_urlopen([200] * 3)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    result = rate_limit_probe.probe_rate_limit("https://api.test/x", burst=3)
    assert result["first_throttled_at"] is None
    assert result["throttle_headers"] == {}
    assert len(calls) == 3


def test_probe_honours_custom_throttle_statuses(monkeypatch):
    urlopen, _ = _fake_urlopen([200, 420])
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert rate_limit_probe.probe_rate_limit("https://a.test", burst=2,
                                             rate_limit_statuses={420})["first_throttled_at"] == 1
