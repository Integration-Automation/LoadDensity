# progress.md: LoadDensity

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-2, X-1, X-7, X-12, X-16).

## Open

- **#1** The 2026-05 expansion modules (29 protocol user types, `cloud/`, `engine/`, the 8 new report formats, security / chaos / scenario / governance / ai / data / dx, `deploy/`, `editors/`; commit list in `docs/updates` U-20260922-05) are covered only by `test/test_expansion_smoke.py` and `test/test_expansion2_smoke.py`: add real tests (workspace S-2). The report generators (Allure, cost, CycloneDX, SARIF, service map) have real tests since 2026-09-23; so do `engine/`, `cloud/`, the chaos helpers and the Excel, histogram and PDF writers; so do the scenario/data/dx/governance/ai helpers (U-20260923-15). The protocol user types do not yet.
