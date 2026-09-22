# progress.md: LoadDensity

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-2, X-1, X-7, X-12, X-16).

## Open

- **#1** The 2026-05 expansion modules (29 protocol user types, `cloud/`, `engine/`, the 8 new report formats, security / chaos / scenario / governance / ai / data / dx, `deploy/`, `editors/`; commit list in `docs/updates` U-20260922-05) are covered only by `test/test_expansion_smoke.py` and `test/test_expansion2_smoke.py`: add real tests (workspace S-2).
- **#2** README and the `CLAUDE.md` project-structure section (≈:12-20) do not describe the new modules from #1.
- **#3** Remove the stale `.claude/scheduled_tasks.lock`.
- **#4** The dependabot branch `pyside6-6.10.2` (2026-02-03) is not merged (see workspace X-1).
- **#6** `dev.toml` (the `je_load_density_dev` channel) has no console scripts and only the `gui` extra.
- **#7** `je_load_density/gui/chart_panel.py` and `je_load_density/gui/run_history_panel.py` are not imported by `gui/main_widget.py` or `gui/main_window.py`: wire them in or drop them.
