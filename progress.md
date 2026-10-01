# progress.md: LoadDensity

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-12, X-13).

## Open

- **#22** [BLOCKED: je_action_core on PyPI, ActionCore `progress.md` #1] Install `je_action_core` from PyPI instead of the GitHub pin: remove `[tool.uv.sources]` from `pyproject.toml` and `dev.toml` and run `uv lock`, then drop the "Install je_action_core" step from `ci-dev.yml` and `ci-stable.yml`. Until then, do not release `main`: the published metadata requires `je_action_core`, which PyPI does not have yet.
