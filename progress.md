# progress.md: LoadDensity

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-2, X-1, X-7, X-12, X-16).

## Open

- **#1** The editor extensions under `editors/` (VS Code, Chrome, JetBrains) are not built by any CI job (workspace S-2). The JetBrains plugin builds locally with Gradle 8.10.2 and has a lockfile but no Gradle wrapper (U-20260923-26). The rest of the 2026-05 expansion now has real tests (U-20260923-15, -18, -27) and `deploy/` is checked by `deploy-check.yml` (U-20260923-25).
- **#10** `http3_user_template.py`: the status is hard-coded to 200 and the response is never read, so the documented `expect_status` is ignored and `response_length` is the request body's size (`:94`). From reading the code, `transmit()` is also never called before `wait_closed()` (`:92`), so a real request may never be sent. Fixing it needs a test against a real aioquic server.
