# progress.md: LoadDensity

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-2, X-1, X-7, X-12, X-16).

## Open

- **#1** The editor extensions under `editors/` (VS Code, Chrome, JetBrains) are not built by any CI job (workspace S-2). The JetBrains plugin builds locally with Gradle 8.10.2 and has a lockfile but no Gradle wrapper (U-20260923-26). The rest of the 2026-05 expansion now has real tests (U-20260923-15, -18, -27) and `deploy/` is checked by `deploy-check.yml` (U-20260923-25).
- **#13** [UNVERIFIED] `coap_user_template.py`, `nats_user_template.py` and `opcua_user_template.py` run an asyncio loop per step. Under Locust on Windows, anything in that loop that goes through the loop's thread pool (`loop.getaddrinfo`, `run_in_executor`) never returns, because gevent turns the pool's threads into greenlets (see U-20260923-31 for HTTP/3). Check each against a real server with a hostname target.
