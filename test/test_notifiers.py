import json

from je_load_density.utils.notifier.slack import (
    build_slack_summary,
    post_slack_summary,
)
from je_load_density.utils.notifier.teams import (
    build_teams_summary,
    post_teams_summary,
)


SUMMARY = {
    "totals": {"requests": 1000, "failures": 12, "failure_rate": 0.012,
                "successes": 988},
    "latency_overall": {"p50_ms": 50.0, "p95_ms": 180.0, "p99_ms": 300.0,
                         "max_ms": 500.0, "count": 1000},
    "per_name": {},
}


def test_slack_payload_has_header_and_fields():
    payload = build_slack_summary(SUMMARY, title="Smoke")
    blocks = payload["blocks"]
    assert blocks[0]["type"] == "header"
    assert blocks[0]["text"]["text"] == "Smoke"
    field_texts = [field["text"] for field in blocks[1]["fields"]]
    assert any("1000" in text for text in field_texts)
    assert any("180" in text for text in field_texts)


def test_post_slack_uses_supplied_poster_and_returns_status():
    seen = {}

    def poster(url, body, timeout):
        seen["url"] = url
        seen["body"] = body
        seen["timeout"] = timeout
        return 200

    status = post_slack_summary("https://hook/x", summary=SUMMARY,
                                 timeout=1.0, poster=poster)
    assert status == 200
    assert seen["url"] == "https://hook/x"
    assert seen["timeout"] == 1.0
    body = json.loads(seen["body"])
    assert "blocks" in body


def test_teams_payload_uses_messagecard_schema():
    payload = build_teams_summary(SUMMARY, title="Smoke")
    assert payload["@type"] == "MessageCard"
    facts = payload["sections"][0]["facts"]
    names = {fact["name"] for fact in facts}
    assert {"Requests", "Failures", "Failure rate", "P95 latency"} <= names


def test_post_teams_returns_status_from_poster():
    status = post_teams_summary("https://hook/x", summary=SUMMARY,
                                  poster=lambda *_args: 202)
    assert status == 202
