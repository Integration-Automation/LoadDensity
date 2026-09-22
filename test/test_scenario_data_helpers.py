"""Scenario and test-data helpers: the FSM runner, per-user cookie jars, the user factory,
the PII scrubber and the DB seed/teardown fixtures.

The DB fixtures run against a fake SQLAlchemy (``create_engine`` / ``text``), so the
tests need neither SQLAlchemy nor a database.
"""
import threading
from http.cookiejar import Cookie

import pytest

from je_load_density.utils.data import db_fixtures
from je_load_density.utils.data.factory import build_user, build_user_pool
from je_load_density.utils.data.pii_anonymizer import find_pii, scrub, scrub_string
from je_load_density.utils.scenario import cookie_jar
from je_load_density.utils.scenario.fsm import FsmRunner

_LOGIN_FLOW = [
    {"state": "login", "transitions": {"success": "browse", "failure": "retry"}},
    {"state": "retry", "transitions": {"default": "login"}},
    {"state": "browse", "transitions": {"success": "checkout"}},
    {"state": "checkout", "transitions": {}},
]


# --- FsmRunner -------------------------------------------------------------------------------

def test_fsm_initial_state_is_the_first_named_task():
    runner = FsmRunner([{"payload": "no state"}, *_LOGIN_FLOW])
    assert runner.initial_state == "login"
    assert runner.task_for("browse")["state"] == "browse"
    assert runner.task_for("missing") is None


def test_fsm_without_named_tasks_has_no_initial_state():
    runner = FsmRunner([{"state": ""}, {"payload": 1}])
    assert runner.initial_state is None
    assert runner.run(lambda task: "success") == []


@pytest.mark.parametrize("current, outcome, expected", [
    ("login", "success", "browse"),
    ("login", "failure", "retry"),
    ("login", "timeout", None),  # no match and no default
    ("retry", "anything", "login"),  # default
    ("checkout", "success", None),  # terminal
    ("unknown", "success", None),
])
def test_fsm_next_state(current, outcome, expected):
    assert FsmRunner(_LOGIN_FLOW).next_state(current, outcome) == expected


def test_fsm_self_transition_ends_the_run():
    runner = FsmRunner([{"state": "poll", "transitions": {"default": "poll"}}])
    assert runner.next_state("poll", "success") is None


def test_fsm_ignores_malformed_transitions():
    runner = FsmRunner([{"state": "a", "transitions": ["b"]}])
    assert runner.next_state("a", "success") is None


def test_fsm_run_follows_outcomes_until_terminal():
    outcomes = iter(["failure", "success", "success", "success", "success"])
    history = FsmRunner(_LOGIN_FLOW).run(lambda task: next(outcomes))
    assert [step["state"] for step in history] == ["login", "retry", "login", "browse", "checkout"]
    assert history[0] == {"state": "login", "outcome": "failure"}


def test_fsm_run_stops_at_max_steps():
    runner = FsmRunner([
        {"state": "a", "transitions": {"default": "b"}},
        {"state": "b", "transitions": {"default": "a"}},
    ])
    assert len(runner.run(lambda task: "x", max_steps=5)) == 5


# --- cookie jars ------------------------------------------------------------------------------

def _cookie(name):
    return Cookie(0, name, "v", None, False, "example.test", True, False, "/", True, False, None, False,
                  None, None, {})


@pytest.fixture
def clean_jars():
    cookie_jar.reset_all_jars()
    yield
    cookie_jar.reset_all_jars()


def test_user_jars_are_separate_and_reused(clean_jars):
    first = cookie_jar.jar_for_user(1)
    assert cookie_jar.jar_for_user(1) is first
    assert cookie_jar.jar_for_user(2) is not first


def test_thread_jars_are_per_thread(clean_jars):
    mine = cookie_jar.jar_for_user()
    seen = []
    worker = threading.Thread(target=lambda: seen.append(cookie_jar.jar_for_user()))
    worker.start()
    worker.join()
    assert cookie_jar.jar_for_user() is mine
    assert seen[0] is not mine


def test_reset_user_jar_clears_only_that_user(clean_jars):
    cookie_jar.jar_for_user(1).set_cookie(_cookie("a"))
    cookie_jar.jar_for_user(2).set_cookie(_cookie("b"))
    cookie_jar.reset_user_jar(1)
    cookie_jar.reset_user_jar(99)  # unknown user: no error
    assert len(cookie_jar.jar_for_user(1)) == 0
    assert len(cookie_jar.jar_for_user(2)) == 1


def test_reset_all_jars_forgets_user_jars_and_clears_this_thread(clean_jars):
    old = cookie_jar.jar_for_user(1)
    cookie_jar.jar_for_user().set_cookie(_cookie("t"))
    cookie_jar.reset_all_jars()
    assert cookie_jar.jar_for_user(1) is not old
    assert len(cookie_jar.jar_for_user()) == 0


# --- factory ---------------------------------------------------------------------------------

def test_build_user_has_every_field_and_distinct_values():
    first, second = build_user(), build_user()
    assert set(first) == {"email", "username", "password", "uuid_hex", "int_id"}
    assert first["email"].endswith("@example.test")
    assert len(first["password"]) == 16
    assert len(first["uuid_hex"]) == 32
    assert 0 <= first["int_id"] < 2 ** 31
    assert first["uuid_hex"] != second["uuid_hex"]


def test_build_user_applies_overrides():
    user = build_user({"email": "fixed@example.test", "role": "admin"})
    assert user["email"] == "fixed@example.test"
    assert user["role"] == "admin"


@pytest.mark.parametrize("count, expected", [(3, 3), (0, 0), (-2, 0)])
def test_build_user_pool_size(count, expected):
    assert len(build_user_pool(count)) == expected


def test_build_user_pool_users_are_independent():
    pool = build_user_pool(2, {"tenant": "t1"})
    assert all(user["tenant"] == "t1" for user in pool)
    pool[0]["tenant"] = "changed"
    assert pool[1]["tenant"] == "t1"


# --- PII scrubber ----------------------------------------------------------------------------

def test_scrub_string_replaces_email_and_ip_stably():
    text = "mail a.b@example.com from 10.0.0.12"
    scrubbed = scrub_string(text)
    assert "a.b@example.com" not in scrubbed
    assert "10.0.0.12" not in scrubbed
    assert scrubbed.startswith("mail email_")
    assert " from ip_" in scrubbed
    assert scrub_string(text) == scrubbed  # the same value always maps to the same token


@pytest.mark.parametrize("text", ["", None])
def test_scrub_string_passes_empty_values_through(text):
    assert scrub_string(text) == text


def test_scrub_masks_secret_keys_and_recurses():
    data = {
        "api_key": "k-123",
        "Password": "hunter2",
        "count": 3,
        "nested": [{"email": "x@example.org"}, "plain"],
    }
    scrubbed = scrub(data)
    assert scrubbed["api_key"].startswith("secret_")
    assert scrubbed["Password"].startswith("secret_")
    assert scrubbed["count"] == 3
    assert scrubbed["nested"][0]["email"].startswith("email_")
    assert scrubbed["nested"][1] == "plain"


def test_find_pii_lists_emails():
    assert list(find_pii("a@example.com and b@example.org")) == ["a@example.com", "b@example.org"]
    assert list(find_pii(None)) == []


# --- DB fixtures -----------------------------------------------------------------------------

class _FakeEngine:
    def __init__(self, url, log):
        self.url, self._log = url, log

    def begin(self):
        engine = self

        class _Transaction:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                engine._log.append(("commit", engine.url))
                return False

            def execute(self, statement):
                engine._log.append(("execute", statement))

        return _Transaction()

    def dispose(self):
        self._log.append(("dispose", self.url))


@pytest.fixture
def fake_sqlalchemy(monkeypatch):
    log = []
    monkeypatch.setattr(db_fixtures, "_import_sqlalchemy",
                        lambda: ((lambda url, future: _FakeEngine(url, log)), lambda sql: f"TEXT:{sql}"))
    return log


def test_apply_fixture_runs_setup_and_records_teardown(fake_sqlalchemy):
    fixture = db_fixtures.apply_fixture("sqlite://", ["INSERT 1", "INSERT 2"], ["DELETE 1"])
    assert ("execute", "TEXT:INSERT 1") in fake_sqlalchemy
    assert ("execute", "TEXT:INSERT 2") in fake_sqlalchemy
    assert fixture == {"database_url": "sqlite://", "teardown_sql": ["DELETE 1"]}


def test_run_teardown_executes_recorded_statements(fake_sqlalchemy):
    db_fixtures.run_teardown({"database_url": "sqlite://", "teardown_sql": ["DELETE 1"]})
    assert ("execute", "TEXT:DELETE 1") in fake_sqlalchemy


def test_run_teardown_without_statements_opens_nothing(fake_sqlalchemy):
    db_fixtures.run_teardown({"database_url": "sqlite://", "teardown_sql": []})
    assert fake_sqlalchemy == []


def test_missing_sqlalchemy_is_a_clear_error(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "sqlalchemy", None)
    with pytest.raises(RuntimeError, match="pip install sqlalchemy"):
        db_fixtures.apply_fixture("sqlite://")
