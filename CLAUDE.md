# LoadDensity

Load & Stress Automation Framework built on top of Locust.

## Tech Stack

- Python 3.10+
- Locust (load testing engine)
- PySide6 + qt-material (optional GUI)
- setuptools (build system)

## Project Structure

`architecture.md` §2 has one row per directory; this is the short version.

- `je_load_density/` - main package
  - `wrapper/` - Locust wrappers: `start_test`, environment and runner modes, user templates for 41 user types (HTTP variants and other protocols), per-type proxies, the request hook
  - `utils/` - executor (`LD_*` commands), test records and SQLite persistence, reports (HTML/JSON/XML/CSV/JUnit/summary/chart plus Allure, SARIF, PDF, …), parameterisation, load shapes, SLA gates, importers (HAR, cURL, Postman, OpenAPI, JMeter, k6), metrics sinks and notifiers, socket server, security probes, chaos, scenario FSM and more
  - `engine/` - asyncio HTTP engine without Locust and the `bench` CLI
  - `cloud/` - worker launchers for AWS Fargate/Lambda, Azure ACI and GCP Cloud Run
  - `mcp_server/` - MCP stdio server (JSON-RPC written out, no SDK)
  - `action_lsp/` - LSP server for action JSON; `tools/lint_files.py` is the pre-commit entry
  - `gui/` - optional PySide6 GUI (`gui` extra) with multi-language support
- `editors/` - VS Code, Chrome and JetBrains extensions
- `deploy/` - Helm chart, k8s operator, Terraform, Grafana dashboard, CI templates
- `load_density_driver/` - prebuilt driver
- `test/` - pytest test suite; `test/test_doc_counts.py` fails when a count quoted in `README.md`, `CLAUDE.md` or `architecture.md` no longer matches the code
- `docs/` - Sphinx documentation (`docs/updates/` is the update log, not built)

## Development Commands

```bash
# Install
pip install -e .
pip install -e ".[gui]"

# Test
pytest test/

# Build
python -m build
```

## Coding Standards

### Design Patterns & Software Engineering

- Apply appropriate design patterns (Strategy, Factory, Observer, etc.) where they reduce complexity
- Follow SOLID principles: single responsibility, open-closed, Liskov substitution, interface segregation, dependency inversion
- Prefer composition over inheritance
- Keep functions small and focused on a single task
- Use meaningful, descriptive names for variables, functions, classes, and modules

### Performance

- Avoid unnecessary object creation in hot paths
- Prefer generators over lists for large data iteration
- Use appropriate data structures (set for membership checks, dict for lookups)
- Minimize I/O operations; batch when possible
- Profile before optimizing - measure, don't guess

### Code Hygiene

- Remove all unused imports, variables, functions, classes, and dead code blocks
- No commented-out code in commits
- No placeholder or stub code left behind
- Every import must be used; every function must be called or exported

### Security

- Never hardcode secrets, tokens, passwords, or API keys
- Validate and sanitize all external input (user input, file content, network data)
- Use parameterized queries for any database operations
- Avoid `eval()`, `exec()`, and `__import__()` with untrusted input
- Use `subprocess` with argument lists, never shell=True with user input
- Set restrictive file permissions on sensitive files
- Escape output to prevent injection (HTML, XML, JSON)
- Pin dependency versions to avoid supply chain attacks

### Linter Compliance (SonarQube / Codacy / Pylint / Flake8)

Code must pass static analysis with no new issues introduced. Follow these rules proactively so SonarQube, Codacy, Pylint, Flake8, Bandit, and Radon do not flag regressions.

#### Complexity & Structure

- Cognitive complexity per function: ≤ 15 (SonarQube rule `python:S3776`)
- Cyclomatic complexity per function: ≤ 10 (Radon grade A–B)
- Function length: ≤ 80 lines; file length: ≤ 1000 lines
- Max parameters per function: ≤ 7 (SonarQube `python:S107`)
- Max nesting depth: ≤ 4 levels (SonarQube `python:S134`)
- Avoid deeply nested `if/for/try` — extract helpers or use early returns
- No duplicated code blocks ≥ 10 lines (SonarQube `common-py:DuplicatedBlocks`)
- Keep boolean expressions simple: ≤ 3 operators (SonarQube `python:S1067`)

#### Naming & Style (PEP 8 + Pylint)

- `snake_case` for functions, methods, variables, modules
- `PascalCase` for classes; `UPPER_SNAKE_CASE` for module-level constants
- Private members prefixed with single underscore `_name`
- Line length: ≤ 120 characters (soft limit), hard max 160
- No single-letter names except loop counters (`i`, `j`, `k`) and comprehensions
- Avoid shadowing built-ins (`id`, `list`, `type`, `dict`, `file`, etc.)
- No unused function/method parameters — prefix with `_` if required by signature

#### Bug-Prone Patterns

- Never use mutable default arguments (`def f(x=[])`) — use `None` sentinel (SonarQube `python:S5644`)
- Do not compare with `==` / `!=` to `None`, `True`, `False` — use `is` / `is not`
- Do not catch bare `except:` — catch specific exceptions; never swallow silently
- Always re-raise with `raise` or `raise X from e`, preserving context
- Close resources with `with` context managers (files, sockets, locks)
- Do not modify a collection while iterating over it
- Avoid `assert` for runtime validation (stripped by `python -O`); raise explicit exceptions
- No `TODO` / `FIXME` / `XXX` comments without a tracked issue reference
- Remove unreachable code after `return`, `raise`, `break`, `continue`

#### Type Safety & API Design

- Public functions and methods should have type hints (parameters + return)
- Avoid `Any` unless truly dynamic; prefer `Optional[T]`, `Union[...]`, protocols
- Do not return inconsistent types from one function (e.g. `str` or `None` or `int`)
- Prefer `@dataclass` or `TypedDict` over ad-hoc dict payloads
- Use `enum.Enum` instead of string/int constants for closed sets

#### Security (Bandit + SonarQube Security Hotspots)

- No `eval`, `exec`, `pickle.loads`, `yaml.load` (use `yaml.safe_load`) on untrusted input
- No `hashlib.md5` / `sha1` for security purposes — use `sha256` or `blake2b`
- No `random` module for tokens/secrets — use `secrets` module
- No `tempfile.mktemp` — use `mkstemp` / `NamedTemporaryFile`
- Never log secrets, tokens, or raw request bodies containing credentials
- Validate file paths against traversal (`..`, absolute paths, symlinks)
- Set explicit timeouts on `requests.*` and socket operations

#### Testing Hygiene

- Tests must be deterministic — no reliance on wall-clock, network, or ordering
- Each test asserts something; no test without an `assert`
- Mock external side effects (filesystem writes, HTTP, subprocess)
- Test names describe behavior: `test_<unit>_<condition>_<expected>`

### Git Commit Rules

- Commit messages must NOT reference any AI tool, assistant, or model name
- No `Co-Authored-By` lines referencing AI
- Write commit messages as if authored solely by the developer
- Use conventional commit style: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- Keep subject line under 72 characters
- Use imperative mood ("add feature" not "added feature")

## Documentation

- **README parity.** This repository ships `README.md` (English) alongside the translated `README/README_zh-CN.md` and `README/README_zh-TW.md`. All three must stay current with the code.
- When a change alters anything user-facing — features, commands, CLI flags, install/setup steps, configuration, or requirements — update `README.md`, **both translated READMEs (`README/README_zh-CN.md`, `README/README_zh-TW.md`), and the Sphinx docs under `docs/source/`, all in the same commit**, keeping their section structure and content aligned. Each translation must reflect the English README's actual content, not merely share its headings.
- Never update one language or `README.md` alone and leave the other languages or the docs stale. `test/test_doc_counts.py` catches counts in `README.md` that drift from the code, but it does not check the translations or the docs — keep the language variants and `docs/source/` in sync by hand.

## Stage commits, `progress.md`, `docs/updates/` and `architecture.md`

Workspace rule shared by every repository under `D:\Codes` (full text: `D:\Codes\CLAUDE.md`).

- **Commit at every stage.** A stage is the smallest piece of work that leaves the repository consistent and passes this project's checks (definition of done, tests, lint): one finished `progress.md` item, or one self-contained step of a larger one. Commit it before starting the next stage, before switching to another repository, and before the session ends. Do not leave work uncommitted across sessions; if a stage cannot be finished, commit the consistent part and record the rest in `progress.md`.
  - Stage only the files that stage touched (`git add <path>`, never `git add -A`), follow this file's commit-message rules, and never add AI attribution.
  - Committing is not pushing: push or open a PR only as this project's branch flow says or when asked.
  - **Commit and push frequently.** After each big feature — a self-contained stage that passes this project's checks — commit and push to the remote; do not pile up a large batch of work before committing or pushing. Smaller batches collide less with other sessions, let CI catch problems earlier, and are easier to revert. Follow this project's normal branch flow (usually `dev`).
  - **SonarCloud / Codacy findings.** When a PR or commit fails a SonarCloud or Codacy check, look the findings up through their APIs instead of guessing. The keys are in environment variables: `SonarCloudToken` (SonarCloud, e.g. `curl -s -u "$SonarCloudToken:" "https://sonarcloud.io/api/issues/search?componentKeys=<key>&pullRequest=<n>&resolved=false"`) and `CODACY_PROJECT_TOKEN` (a Codacy project token, valid only for its own project: any other repository answers "Bad credentials", so for a public repository query `https://app.codacy.com/api/v3/analysis/organizations/gh/<org>/repositories/<repo>/pull-requests/<n>/issues?status=new` without a key). **Never reveal a key or any personal credential while doing so**: refer to the variables by name only, never echo or print their values, and never put them in files, commit messages, PR or issue text, logs, or any output that leaves the machine.
- **`progress.md`** (repository root, tracked) holds outstanding work only: no finished items, no history, no rules.
- **`docs/updates/`** records finished work: one batch file per month (`YYYY-MM.md`), one entry per piece of work headed `## U-YYYYMMDD-NN · date · title · #tags`, and an index with query commands in `docs/updates/README.md`. When a `progress.md` item is done, delete it and add a `#done` entry plus its index row in the same commit.
- **`architecture.md`** (repository root) is the short architecture overview: layers, entry points, main flows, extension points, cross-project boundaries. Update it in the same commit whenever a change alters any of those.
- **Cross-project contracts** are listed in `architecture.md` §6: what other repositories rely on here (CLI flags, import paths, constructor arguments, file layouts) and what this repository relies on elsewhere. No test here protects them, so never rename or remove one without changing its consumers in the same round, and update §6 whenever a contract is added or changes.
