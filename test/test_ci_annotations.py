import io

import pytest

from je_load_density.utils.ci_annotations.github_actions import (
    emit_github_annotations,
    format_github_annotation,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance


def test_format_annotation_error_with_options():
    line = format_github_annotation(
        "error", "boom",
        file="actions/smoke.json", line=12, title="LD",
    )
    assert line.startswith("::error ")
    assert "file=actions/smoke.json" in line
    assert "line=12" in line
    assert "title=LD" in line
    assert line.endswith("boom")


def test_format_annotation_rejects_unknown_severity():
    with pytest.raises(ValueError):
        format_github_annotation("info", "x")


def test_format_annotation_escapes_newlines_in_message():
    line = format_github_annotation("warning", "first\nsecond")
    assert "%0A" in line
    assert "\n" not in line.split("::", 2)[2]


def test_emit_writes_one_annotation_per_failure():
    test_record_instance.test_record_list.clear()
    test_record_instance.error_record_list.clear()
    test_record_instance.error_record_list.extend([
        {"Method": "GET", "test_url": "/a", "status_code": "500", "error": "boom"},
        {"Method": "POST", "test_url": "/b", "status_code": None, "error": "timeout"},
    ])
    try:
        sink = io.StringIO()
        written = emit_github_annotations(stream=sink)
        assert written == 2
        lines = sink.getvalue().strip().splitlines()
        assert all(line.startswith("::error") for line in lines)
        assert "GET /a (HTTP 500)" in lines[0]
        assert "POST /b" in lines[1]
    finally:
        test_record_instance.error_record_list.clear()
