"""Real tests for the ``utils/ai`` helpers: SLA auto-baseline, the auto-tuner, the root-cause prompt
builder and the breaking-point search.

The SQLite trend store is either stubbed or built in ``tmp_path``; ``git`` is replaced by a stand-in for
``subprocess.run``. No LLM, network or real load test is involved.
"""
import sqlite3
from types import SimpleNamespace

import pytest

from je_load_density.utils.ai import auto_baseline, root_cause
from je_load_density.utils.ai.auto_tune import AutoTuner
from je_load_density.utils.ai.smart_shape import find_breaking_point
from je_load_density.utils.test_record.sqlite_persistence import _SCHEMA


def _stub_trend(monkeypatch, per_run):
    calls = []

    def fake_trend_runs(database_path, limit, name_filter):
        calls.append((database_path, limit, name_filter))
        return {"per_run": per_run}

    monkeypatch.setattr(auto_baseline, "trend_runs", fake_trend_runs)
    return calls


def _rules_by_type(rules):
    return {rule["type"]: rule for rule in rules}


# --- auto_baseline ---------------------------------------------------------------------------------

def test_calibrate_sla_returns_empty_when_no_runs(monkeypatch):
    _stub_trend(monkeypatch, [])
    assert auto_baseline.calibrate_sla("db.sqlite") == []


def test_calibrate_sla_passes_arguments_through(monkeypatch):
    calls = _stub_trend(monkeypatch, [])
    auto_baseline.calibrate_sla("x.db", runs_to_use=4, name_filter="/api")
    assert calls == [("x.db", 4, "/api")]


def test_calibrate_sla_uses_max_p95_with_headroom(monkeypatch):
    _stub_trend(monkeypatch, [
        {"p95_ms": 100, "failure_rate": 0.02, "requests": 100},
        {"p95_ms": 200, "failure_rate": 0.05, "requests": 301},
    ])
    rules = _rules_by_type(auto_baseline.calibrate_sla("db", tolerance_pct=10.0))
    assert rules["latency_p95"]["value"] == pytest.approx(220.0)
    assert rules["latency_p95"]["note"] == "max observed * 1.10"
    assert rules["failure_rate"]["value"] == pytest.approx(0.055)


def test_calibrate_sla_request_floor_is_half_the_median(monkeypatch):
    _stub_trend(monkeypatch, [{"requests": 100}, {"requests": 300}, {"requests": 1000}])
    rules = _rules_by_type(auto_baseline.calibrate_sla("db"))
    assert rules["requests"] == {"type": "requests", "op": "gte", "value": 150}


def test_calibrate_sla_failure_rate_has_one_percent_floor(monkeypatch):
    _stub_trend(monkeypatch, [{"p95_ms": 50, "failure_rate": 0.0, "requests": 10}])
    rules = _rules_by_type(auto_baseline.calibrate_sla("db"))
    assert rules["failure_rate"]["value"] == 0.01


def test_calibrate_sla_reads_real_sqlite_store(tmp_path):
    database = tmp_path / "runs.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(_SCHEMA)
    connection.execute("INSERT INTO load_density_runs (started_at, label) VALUES ('t0', 'a')")
    for latency in (10.0, 20.0, 30.0, 40.0):
        connection.execute(
            "INSERT INTO load_density_records (run_id, outcome, name, response_time_ms) VALUES (1, 'success', 'n', ?)",
            (latency,),
        )
    connection.commit()
    connection.close()
    rules = _rules_by_type(auto_baseline.calibrate_sla(str(database), tolerance_pct=0.0))
    assert rules["latency_p95"]["value"] == 40.0
    assert rules["requests"]["value"] == 2


# --- auto_tune -------------------------------------------------------------------------------------

def test_auto_tuner_rejects_non_positive_target():
    with pytest.raises(ValueError):
        AutoTuner(target_p95_ms=0)


def test_auto_tuner_scales_up_when_under_budget():
    tuner = AutoTuner(target_p95_ms=100, initial_users=10)
    assert tuner.next_step(50) == {"users": 12, "spawn_rate": 2}


def test_auto_tuner_scales_down_when_over_budget():
    tuner = AutoTuner(target_p95_ms=100, initial_users=10)
    assert tuner.next_step(200)["users"] == 5


def test_auto_tuner_nudges_by_one_when_proportional_step_rounds_away():
    tuner = AutoTuner(target_p95_ms=100, initial_users=1)
    assert tuner.next_step(90)["users"] == 2


def test_auto_tuner_holds_steady_on_target_and_on_non_positive_measurement():
    tuner = AutoTuner(target_p95_ms=100, initial_users=10)
    tuner.next_step(100)
    tuner.next_step(0)
    assert [row["users"] for row in tuner.history] == [10, 10]
    assert tuner.history[1]["measured_p95_ms"] == 100


def test_auto_tuner_clamps_to_bounds():
    tuner = AutoTuner(target_p95_ms=100, initial_users=10, max_users=11, min_users=3)
    assert tuner.next_step(1)["users"] == 11
    assert tuner.next_step(10_000)["users"] == 3


def test_auto_tuner_spawn_rate_is_a_fifth_of_users_with_floor_of_one():
    tuner = AutoTuner(target_p95_ms=100, initial_users=50, gain=0.0)
    assert tuner.next_step(100)["spawn_rate"] == 10
    small = AutoTuner(target_p95_ms=100, initial_users=2, gain=0.0)
    assert small.next_step(100)["spawn_rate"] == 1


def test_auto_tuner_run_feeds_measure_step_and_records_history():
    seen = []

    def measure(users, spawn_rate, step_seconds):
        seen.append((users, spawn_rate, step_seconds))
        return "50"

    tuner = AutoTuner(target_p95_ms=100, initial_users=10, initial_spawn_rate=3, step_seconds=1.5)
    history = tuner.run(2, measure)
    assert seen == [(10, 3, 1.5), (12, 2, 1.5)]
    assert [row["users"] for row in history] == [12, 15]


# --- root_cause ------------------------------------------------------------------------------------

def test_git_diff_stat_returns_none_without_git(monkeypatch):
    monkeypatch.setattr(root_cause.shutil, "which", lambda _name: None)
    assert root_cause._git_diff_stat() is None


def test_git_diff_stat_decodes_stdout_and_builds_command(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="commit abc\n é".encode("utf-8"))

    monkeypatch.setattr(root_cause.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(root_cause.subprocess, "run", fake_run)
    assert root_cause._git_diff_stat(commits=3, timeout=2.0) == "commit abc\n é"
    assert calls[0][0] == ["/usr/bin/git", "log", "--stat", "-3"]
    assert calls[0][1]["timeout"] == 2.0


def test_git_diff_stat_returns_none_on_failure_or_timeout(monkeypatch):
    monkeypatch.setattr(root_cause.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(root_cause.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=128, stdout=b"x"))
    assert root_cause._git_diff_stat() is None

    def boom(*_args, **_kwargs):
        raise root_cause.subprocess.TimeoutExpired("git", 5)

    monkeypatch.setattr(root_cause.subprocess, "run", boom)
    assert root_cause._git_diff_stat() is None


def test_build_root_cause_prompt_keeps_top_five_clusters_and_skips_git():
    clusters = [{"id": index} for index in range(8)]
    context = root_cause.build_root_cause_prompt(
        {"delta": 1}, clusters, {"requests": 3}, extra_context="deploy at 10:00", include_git_log=False,
    )
    assert [row["id"] for row in context["top_error_clusters"]] == [0, 1, 2, 3, 4]
    assert context["recent_git_log"] is None
    assert context["summary"] == {"requests": 3}
    assert context["extra_context"] == "deploy at 10:00"


def test_build_root_cause_prompt_includes_git_log(monkeypatch):
    monkeypatch.setattr(root_cause, "_git_diff_stat", lambda: "stat output")
    context = root_cause.build_root_cause_prompt({}, [], {})
    assert context["recent_git_log"] == "stat output"


def test_render_prompt_text_embeds_json_sections_and_placeholders():
    context = root_cause.build_root_cause_prompt(
        {"p95": 12}, [{"message": "timeout"}], {"requests": 7}, include_git_log=False,
    )
    text = root_cause.render_prompt_text(context)
    assert text.startswith(context["task"])
    assert '"requests": 7' in text
    assert '"message": "timeout"' in text
    assert "## Recent git log\n```\n(none)\n```" in text
    assert text.endswith("## Extra context\n(none)\n")


# --- smart_shape -----------------------------------------------------------------------------------

@pytest.mark.parametrize("bounds", [(0, 10), (5, 5), (10, 3)])
def test_find_breaking_point_rejects_invalid_bounds(bounds):
    with pytest.raises(ValueError, match="bounds"):
        find_breaking_point(lambda _u: 0.0, min_users=bounds[0], max_users=bounds[1])


@pytest.mark.parametrize("threshold", [-0.1, 1.5])
def test_find_breaking_point_rejects_threshold_outside_unit_interval(threshold):
    with pytest.raises(ValueError, match="failure_threshold"):
        find_breaking_point(lambda _u: 0.0, failure_threshold=threshold)


def test_find_breaking_point_finds_threshold_and_records_history():
    result = find_breaking_point(lambda users: 0.0 if users <= 500 else 0.5, max_iterations=20)
    assert result["safe_users"] == 500
    assert result["history"][0] == {"users": 500, "failure_rate": 0.0}
    assert all((row["failure_rate"] == 0.0) == (row["users"] <= 500) for row in result["history"])


def test_find_breaking_point_respects_iteration_cap():
    probed = []

    def probe(users):
        probed.append(users)
        return 0.0

    result = find_breaking_point(probe, max_iterations=3)
    assert probed == [500, 750, 875]
    assert result["safe_users"] == 875


def _limit_probe(limit, probed=None):
    def probe(users):
        if probed is not None:
            probed.append(users)
        return 0.0 if users <= limit else 1.0
    return probe


@pytest.mark.parametrize("min_users, max_users, limit, expected", [
    (1, 2, 10, 2),  # everything passes: the answer is the upper bound
    (1, 1000, 1000, 1000),
    (1, 1000, 600, 600),  # 600 passes, 601 fails
    (1, 1000, 1, 1),
])
def test_find_breaking_point_returns_the_largest_safe_count(min_users, max_users, limit, expected):
    result = find_breaking_point(_limit_probe(limit), min_users=min_users, max_users=max_users)
    assert result["safe_users"] == expected


def test_find_breaking_point_reports_zero_when_even_the_minimum_fails():
    probed = []
    result = find_breaking_point(_limit_probe(0, probed), min_users=1, max_users=10)
    assert result["safe_users"] == 0
    assert 1 in probed
