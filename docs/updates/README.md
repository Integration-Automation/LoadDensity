# docs/updates: update log index

`progress.md` holds only work that is **not done yet**. Everything that *was* done (what changed, measured numbers, decisions, snapshots) is recorded here: **one batch file per month**, one entry per piece of work, each entry with a fixed-format ID and tags, and one row per entry in the index below.

> No TODOs here. If an entry mentions something still open, it only points to it (e.g. "open item: `progress.md` #3"); the item itself lives in `progress.md`.

## How to query

Run from the repository root:

| To find | Command |
|---|---|
| every entry, one line each | `rg -n "^## U-2" docs/updates` |
| entries of one type | `rg -n "^## U-2.*#done" docs/updates` |
| entries with a topic tag | `rg -n "^## U-2.*#<tag>" docs/updates` |
| one day or one month | `rg -n "^## U-202609" docs/updates` |
| the full text of one entry | `rg -n -A 60 "^## U-20260922-01" docs/updates` |
| any keyword | `rg -n "keyword" docs/updates` |

Without `rg`: `git grep -n "^## U-2" -- docs/updates`, or in PowerShell `Select-String -Path docs/updates/*.md -Pattern '^## U-2'`.

## Entry format

```markdown
## U-YYYYMMDD-NN · YYYY-MM-DD · one-line title · #type #topic

- **What**: ...
- **Result / numbers**: ...
- **Files**: `path` ...
- **Evidence**: commit, file:line, link ...
- **Open items**: none / see `progress.md` ...
```

- **ID**: `U-` + date + two-digit sequence for that day. IDs are never renumbered or reused, so code comments and other documents can cite them.
- **Type tag** (exactly one): `#done` finished `progress.md` item, `#snapshot` measurement or inventory, `#decision`, `#incident`, `#migration`, `#docs`, `#release`.
- Topic tags are free-form (`#mcp`, `#wayland`, ...).
- Keep conclusions, numbers, files and evidence; drop the reasoning trail and dead ends.

## Batch rules

1. One file per month: `docs/updates/YYYY-MM.md`. Append new entries at the end.
2. Over about 800 lines, continue in `YYYY-MM-b.md` (then `-c`) and list it in the batch table below.
3. **Claim the ID under a lock.** Several sessions may write this log at the same time (for example parallel autonomous runs), and without a lock two of them pick the same number:
   1. `mkdir docs/updates/.id-lock`. Creating a directory is atomic, so only one writer succeeds. If it already exists, someone else is claiming: wait a few seconds and retry. A lock older than 10 minutes is stale and may be removed.
   2. Find the day's last number with `rg -n "^## U-YYYYMMDD" docs/updates` and write the heading line and the index row.
   3. `rmdir docs/updates/.id-lock`, then fill in the body. Git never tracks the empty lock directory.
   4. Before committing, `rg -c "^## U-<your ID>" docs/updates` must report one match in total. If not, renumber your entry under the lock and fix its index row. Whoever merges a branch renumbers entries that reuse an ID.
4. **One line per index row**: title only (about 60 characters), no summary.
5. Never rewrite a recorded entry. Correct it with a new `#decision` or `#incident` entry and add "→ corrected in U-..." to the old one.

## When a `progress.md` item is done

In the same commit: delete the item from `progress.md`, add a `#done` entry here that names it, and add its index row.

---

## Index (newest first)

| ID | Date | Title | Tags | Batch |
|---|---|---|---|---|
| U-20260923-25 | 2026-09-23 | Terraform module and operator image fixed; deploy/ is checked in CI | #done #bugfix #deploy #ci | [2026-09](2026-09.md) |
| U-20260923-24 | 2026-09-23 | Deploy manifests bounded; operator image runs as non-root | #done #deploy #security | [2026-09](2026-09.md) |
| U-20260923-23 | 2026-09-23 | generate_from_openapi works again; MCP tool paths are confined | #bugfix #security | [2026-09](2026-09.md) |
| U-20260923-22 | 2026-09-23 | Template setters' host and connection are step defaults | #done #bugfix | [2026-09](2026-09.md) |
| U-20260923-21 | 2026-09-23 | Python 3.10 import restored; XML refusals become XMLException | #bugfix #ci | [2026-09](2026-09.md) |
| U-20260923-20 | 2026-09-23 | cryptography floor 50 | #done #deps #security | [2026-09](2026-09.md) |
| U-20260923-19 | 2026-09-23 | Nine bugs in the protocol user templates | #bugfix | [2026-09](2026-09.md) |
| U-20260923-18 | 2026-09-23 | Protocol user templates have real tests | #tests | [2026-09](2026-09.md) |
| U-20260923-17 | 2026-09-23 | Counts quoted in the docs are checked against the code | #done #docs #tests | [2026-09](2026-09.md) |
| U-20260923-16 | 2026-09-23 | Five bugs found by those tests | #bugfix #security #performance | [2026-09](2026-09.md) |
| U-20260923-15 | 2026-09-23 | Real tests for the scenario, data, dx, governance and ai helpers | #tests | [2026-09](2026-09.md) |
| U-20260923-14 | 2026-09-23 | LoadDensity.log moves out of the working directory | #done #logging | [2026-09](2026-09.md) |
| U-20260923-13 | 2026-09-23 | Cloud launchers tested; warm Lambdas report their own run | #done #bugfix #tests | [2026-09](2026-09.md) |
| U-20260923-12 | 2026-09-23 | Excel output opens again; PDF titles and control characters handled | #done #bugfix #tests | [2026-09](2026-09.md) |
| U-20260923-11 | 2026-09-23 | Chaos helpers tested; Toxiproxy names are quoted | #done #bugfix #tests | [2026-09](2026-09.md) |
| U-20260923-10 | 2026-09-23 | Asyncio engine counts 4xx/5xx as failures and times the load, not the setup | #done #bugfix #tests | [2026-09](2026-09.md) |
| U-20260923-09 | 2026-09-23 | Report generators tested; service map follows real request order | #done #bugfix #tests | [2026-09](2026-09.md) |
| U-20260923-08 | 2026-09-23 | README covers the 2026-05 modules | #done #docs | [2026-09](2026-09.md) |
| U-20260923-07 | 2026-09-23 | CLAUDE.md project structure matches the package | #docs | [2026-09](2026-09.md) |
| U-20260923-06 | 2026-09-23 | Live chart and run history reachable from the GUI | #done #gui | [2026-09](2026-09.md) |
| U-20260923-05 | 2026-09-23 | dev.toml matches pyproject.toml; stale task lock removed | #done #packaging | [2026-09](2026-09.md) |
| U-20260923-04 | 2026-09-23 | PySide6 6.11.2 and Dependabot on dev | #done #deps #ci | [2026-09](2026-09.md) |
| U-20260923-03 | 2026-09-23 | Executor builtins become an allowlist | #done #security #executor | [2026-09](2026-09.md) |
| U-20260923-02 | 2026-09-23 | MCP server answers again: JSON-RPC over stdio without the SDK | #done #mcp #bugfix | [2026-09](2026-09.md) |
| U-20260923-01 | 2026-09-23 | Clear the Dependabot alerts in uv.lock and the VS Code extension | #done #security #deps | [2026-09](2026-09.md) |
| U-20260922-05 | 2026-09-22 | Commit the 2026-05 expansion in stages | #done #expansion | [2026-09](2026-09.md) |
| U-20260922-04 | 2026-09-22 | Contract test for the legacy CLI flags | #done #tests | [2026-09](2026-09.md) |
| U-20260922-03 | 2026-09-22 | Point project URLs at the Integration-Automation org | #done #metadata | [2026-09](2026-09.md) |
| U-20260922-02 | 2026-09-22 | Stop tracking .idea/ | #done #housekeeping | [2026-09](2026-09.md) |
| U-20260922-01 | 2026-09-22 | Adopt progress/architecture/docs-updates rules | #docs #migration | [2026-09](2026-09.md) |

## Batches

| File | Period | Entries |
|---|---|---:|
| [2026-09.md](2026-09.md) | 2026-09 | 30 |
