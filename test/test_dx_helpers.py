"""Real tests for the ``utils/dx`` helpers: message localisation, the tracemalloc leak detector, the
cProfile / tracemalloc wrappers and the REPL bootstrap.

The leak detector's sample buffer is seeded directly through ``monkeypatch``; the REPL console is
replaced by a recorder, so no interactive prompt is opened.
"""
import threading
import time
import tracemalloc

import pytest

from je_load_density.utils.dx import i18n, leak_detector, profiler, repl


# --- i18n ------------------------------------------------------------------------------------------

def test_available_locales_are_sorted_and_complete():
    assert i18n.available_locales() == ["en", "ja", "ko", "zh-CN", "zh-TW"]


def test_every_locale_translates_every_english_key():
    english_keys = set(i18n._MESSAGES["en"])
    for locale in i18n.available_locales():
        assert set(i18n._MESSAGES[locale]) == english_keys, locale


def test_translate_with_explicit_locale():
    assert i18n.t("cant_find_json", "zh-TW") == "找不到 action JSON 檔案。"


def test_translate_uses_env_locale_and_defaults_to_english(monkeypatch):
    monkeypatch.setenv("LD_LOCALE", "ja")
    assert i18n.get_current_locale() == "ja"
    assert i18n.t("missing_locust") == "start_test を呼ぶには Locust が必要です。"
    monkeypatch.delenv("LD_LOCALE")
    assert i18n.get_current_locale() == "en"
    assert i18n.t("missing_locust") == "Locust is required to run start_test."


def test_translate_unknown_locale_falls_back_to_english():
    assert i18n.t("missing_extra", "fr") == "Optional dependency not installed."


def test_translate_unknown_key_returns_key():
    assert i18n.t("no_such_key", "ko") == "no_such_key"


# --- leak_detector ---------------------------------------------------------------------------------

def _sample(*rows):
    return {"ts": 0.0, "rows": [(trace, size, 1) for trace, size in rows]}


def _seed(monkeypatch, samples):
    monkeypatch.setitem(leak_detector._state, "samples", samples)


def test_detect_requires_min_samples(monkeypatch):
    _seed(monkeypatch, [_sample(("a.py:1", 10)), _sample(("a.py:1", 20))])
    assert leak_detector.detect_growing_allocations(min_samples=3) == []


def test_detect_reports_monotonic_growth_sorted_by_growth(monkeypatch):
    _seed(monkeypatch, [
        _sample(("a.py:1", 10), ("b.py:2", 100)),
        _sample(("a.py:1", 10), ("b.py:2", 150)),
        _sample(("a.py:1", 30), ("b.py:2", 400)),
    ])
    suspects = leak_detector.detect_growing_allocations()
    assert [row["trace"] for row in suspects] == ["b.py:2", "a.py:1"]
    assert suspects[0] == {"trace": "b.py:2", "first_bytes": 100, "last_bytes": 400, "growth_bytes": 300}


def test_detect_ignores_flat_shrinking_and_sparse_traces(monkeypatch):
    _seed(monkeypatch, [
        _sample(("flat", 5), ("dip", 10), ("sparse", 1)),
        _sample(("flat", 5), ("dip", 5)),
        _sample(("flat", 5), ("dip", 50), ("sparse", 9)),
    ])
    assert leak_detector.detect_growing_allocations() == []


def test_detect_with_no_samples(monkeypatch):
    _seed(monkeypatch, [])
    assert leak_detector.detect_growing_allocations(min_samples=1) == []


def test_start_and_stop_leak_detector_collects_bounded_samples():
    was_tracing = tracemalloc.is_tracing()
    leak_detector.start_leak_detector(interval_seconds=0.01, max_samples=2)
    try:
        thread = leak_detector._state["thread"]
        leak_detector.start_leak_detector(interval_seconds=0.01, max_samples=2)
        assert leak_detector._state["thread"] is thread
        deadline = time.monotonic() + 5
        while len(leak_detector._state["samples"]) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        leak_detector.stop_leak_detector()
    samples = leak_detector._state["samples"]
    assert 1 <= len(samples) <= 2
    assert all(isinstance(row[1], int) for row in samples[0]["rows"])
    assert leak_detector._state["thread"] is None
    assert not thread.is_alive()
    if not was_tracing:
        assert not tracemalloc.is_tracing()


def test_stop_leak_detector_without_start_is_a_no_op(monkeypatch):
    stop_event = threading.Event()
    monkeypatch.setitem(leak_detector._state, "thread", None)
    monkeypatch.setitem(leak_detector._state, "stop", stop_event)
    leak_detector.stop_leak_detector()
    assert not stop_event.is_set()


# --- profiler --------------------------------------------------------------------------------------

def _work(count, *, scale=1):
    return sum(index * scale for index in range(count))


def test_profile_call_returns_result_and_report():
    result, report = profiler.profile_call(_work, 100, scale=2)
    assert result == 9900
    assert "_work" in report
    assert "cumulative" in report


def test_profile_call_propagates_exceptions():
    def fail():
        raise KeyError("boom")

    with pytest.raises(KeyError):
        profiler.profile_call(fail)


def test_memory_snapshot_returns_result_and_top_allocations():
    if tracemalloc.is_tracing():
        pytest.skip("tracemalloc already tracing in this process")
    result, report = profiler.memory_snapshot(lambda: [bytes(1024) for _ in range(50)], top_n=3)
    assert len(result) == 50
    rows = report["top_allocations"]
    assert 1 <= len(rows) <= 3
    assert set(rows[0]) == {"trace", "size_bytes", "count"}
    assert not tracemalloc.is_tracing()


def test_memory_snapshot_stops_tracing_when_callable_raises():
    if tracemalloc.is_tracing():
        pytest.skip("tracemalloc already tracing in this process")

    def fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        profiler.memory_snapshot(fail)
    assert not tracemalloc.is_tracing()


# --- repl ------------------------------------------------------------------------------------------

class _FakeConsole:
    instances: list = []

    def __init__(self, locals=None):  # noqa: A002 - mirrors code.InteractiveConsole
        self.namespace = locals
        self.interact_kwargs = None
        type(self).instances.append(self)

    def interact(self, **kwargs):
        self.interact_kwargs = kwargs


@pytest.fixture()
def fake_console(monkeypatch):
    _FakeConsole.instances = []
    monkeypatch.setattr(repl.code, "InteractiveConsole", _FakeConsole)
    return _FakeConsole


def test_start_repl_preloads_package_and_uses_default_banner(fake_console):
    import je_load_density

    repl.start_repl()
    console = fake_console.instances[0]
    assert console.namespace == {"ld": je_load_density}
    assert console.interact_kwargs == {"banner": repl._BANNER, "exitmsg": ""}


def test_start_repl_uses_custom_banner(fake_console):
    repl.start_repl(banner="hello")
    assert fake_console.instances[0].interact_kwargs["banner"] == "hello"
