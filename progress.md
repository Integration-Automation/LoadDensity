# progress.md: LoadDensity

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-2, X-1, X-7, X-12, X-16).

## Open

- **#1** About 162 files of work from 2026-05-25..27 are still uncommitted (29 protocol user templates and proxies, `cloud/`, the asyncio `engine/`, 7 report formats, security / chaos / governance / ai / dx modules, `deploy/`, `editors/`). Only `test_expansion_smoke.py` and `test_expansion2_smoke.py` cover them: add real tests, then commit in stages (workspace S-2).
- **#2** README and the `CLAUDE.md` project-structure section (≈:12-20) do not describe the new modules from #1.
- **#3** Remove the stale `.claude/scheduled_tasks.lock`.
- **#4** The dependabot branch `pyside6-6.10.2` (2026-02-03) is not merged (see workspace X-1).
- **#5** The modified tracked files (`__init__.py`, `__main__.py`, the executor, `mcp_server/server.py`, `proxy_user.py`, `start_test.py`, `pyproject.toml`) import the untracked modules from #1, so the working tree only works as a whole: commit #1 together with them.
- **#6** `dev.toml` (the `je_load_density_dev` channel) has no console scripts and only the `gui` extra.
