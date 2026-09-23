# progress.md: LoadDensity

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: S-2, X-1, X-7, X-12, X-16).

## Open

- **#1** Parts of the 2026-05 expansion (commit list in `docs/updates` U-20260922-05) are still covered only by `test/test_expansion_smoke.py` and `test/test_expansion2_smoke.py` (workspace S-2): the probes in `je_load_density/utils/security/` (fuzz, graphql, jwt, owasp, rate-limit, smuggling, ssrf), and `editors/` (VS Code, Chrome, JetBrains), whose builds no check runs. The JetBrains plugin also has no Gradle wrapper or lockfile (SonarCloud text:S8569). `deploy/` is checked by `deploy-check.yml` (U-20260923-25).
- **#10** `http3_user_template.py`: the status is hard-coded to 200 and the response is never read, so the documented `expect_status` is ignored and `response_length` is the request body's size (`:94`). From reading the code, `transmit()` is also never called before `wait_closed()` (`:92`), so a real request may never be sent. Fixing it needs a test against a real aioquic server.
- **#12** Fourteen protocol templates store the `connection` given to their setter but never read it: amqp, coap, elasticsearch, ftp, fuzz_http, graphql_ws, http3, imap, ldap, modbus, nats, opcua, pulsar, sftp. Route them through `with_connection_defaults` (`wrapper/user_template/_common.py`), as the eleven fixed in U-20260923-22 do, or stop accepting the argument.
