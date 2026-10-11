# Desktop GUI lifecycle execution plan

Approved roadmap: `docs/superpowers/specs/2026-10-02-testing-platform-roadmap.md`, UI section, items 18/24.

- Preserve public controls and the Log / Live Chart / Run History tab contract while arranging settings left and run inspection right. Translate new settings, states, request results and controls in all four existing languages.
- Replace the Qt thread's direct engine call with a fresh interpreter for every run. The parent imports no Locust; the child selects the scheduler before starting its metrics pump.
- Pass a unique control file through `stop_requested`, collect environment handles through `on_environment`, signal all background updates to Qt, reject duplicate starts and bound close/join cleanup. Escalate child termination after a three second cooperative grace period.
- Transport cumulative metrics and at most 200 sanitized request rows. Keep at most 500 log blocks and freeze completed charts. Preserve workload arguments and report actions in action files, while recording all action failures as a failed terminal state.
- Verify initial red lifecycle contracts, focused regression tests, existing tabs/bands, and a required offscreen installed-wheel probe against an independent local HTTP server. Exercise completion/cancellation for Locust and asyncio, then close an active run and confirm no child or QThread survives.

Official API references: [Qt QThread wait and signal threading](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html), [Qt QProcess lifecycle and native bounded waits](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html). The supervisor and smoke HTTP server use QProcess rather than monkey-patched Python subprocess/thread/queue I/O.

Final bounded-frame regression: 200 request rows with long CJK names plus 120 complete window aggregates serialize to 618,967 bytes without limiting and exceed the unchanged 131,072-byte reader cap. The serializer preserves the full cumulative summary and all bounded aggregates, then retains the latest complete request rows under that byte limit. The regression frame is 129,733 bytes, retains the latest 38 rows through request 199 and all 120 windows, and still reports 200 total requests; the source snapshot remains unmodified.

Chart accuracy regression: 250 requests at epoch 100.5 with latency 10 ms plus 250 at epoch 101.5 with latency 100 ms retain only 200 rows in the request table, but both rendered child windows retain their true count of 250 and p95 values of 10/100 ms. The chart consumes aggregates computed from complete child records, retains up to 120 windows, and preserves default global-record behavior for callers that do not supply snapshots.

Final GUI lifecycle/tabs/bands verification: 25 passed; bounded Ruff checks passed. The final source Locust-prepatched HTTP completion/cancel/close probe also passed. Earlier installed-wheel checks passed before these final serialization/window-aggregate changes; the integrating agent rebuilds the final wheel.

Ownership: `gui/*`, including the approved direct-window snapshot adapter in `chart_panel.py`; `test/test_gui_lifecycle.py`; `test/smoke/gui_probe.py`; and only `platform_probes.gui`. Existing band rendering and default global-record behavior remain covered by their original tests. Shared docs and commits belong to the integrating agent.
