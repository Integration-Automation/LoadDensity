from je_load_density.utils.linter.action_linter import lint_action


KNOWN = {"LD_start_test", "LD_summary", "LD_generate_summary_report"}


def _rules(findings):
    return [f["rule"] for f in findings]


def test_lint_action_accepts_valid_smoke_with_placeholder():
    actions = {"load_density": [
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "tasks": [{"method": "get", "request_url": "${var.base}/get"}],
        }],
        ["LD_summary"],
    ]}
    assert lint_action(actions, known_commands=KNOWN) == []


def test_lint_action_flags_unknown_command():
    actions = [["LD_bogus_command", {}]]
    findings = lint_action(actions, known_commands=KNOWN)
    assert "unknown-command" in _rules(findings)


def test_lint_action_flags_hardcoded_url():
    actions = [["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "tasks": [{"method": "get", "request_url": "https://prod.example.com/api"}],
    }]]
    findings = lint_action(actions, known_commands=KNOWN)
    assert "hardcoded-url" in _rules(findings)


def test_lint_action_flags_missing_tasks():
    actions = [["LD_start_test", {"user_detail_dict": {"user": "fast_http_user"}}]]
    findings = lint_action(actions, known_commands=KNOWN)
    assert "missing-tasks" in _rules(findings)


def test_lint_action_flags_invalid_shape():
    actions = [["LD_start_test"], "not-a-list"]
    findings = lint_action(actions, known_commands=KNOWN)
    assert "invalid-shape" in _rules(findings)


def test_lint_action_rejects_non_list_top_level():
    findings = lint_action("not-a-list", known_commands=KNOWN)
    assert findings and findings[0]["rule"] == "invalid-shape"


def test_lint_action_handles_dict_form_tasks():
    actions = [["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "tasks": {"mode": "weighted", "tasks": [
            {"method": "get", "request_url": "${var.base}/x"},
        ]},
    }]]
    assert lint_action(actions, known_commands=KNOWN) == []


def test_lint_action_flags_oversize_body():
    big_body = "x" * (1024 * 1024 + 1)
    actions = [["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "tasks": [{"method": "post", "request_url": "${var.base}/x", "data": big_body}],
    }]]
    findings = lint_action(actions, known_commands=KNOWN)
    assert "oversize-body" in _rules(findings)
