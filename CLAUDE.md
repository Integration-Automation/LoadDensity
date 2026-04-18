# LoadDensity

Load & Stress Automation Framework built on top of Locust.

## Tech Stack

- Python 3.10+
- Locust (load testing engine)
- PySide6 + qt-material (optional GUI)
- setuptools (build system)

## Project Structure

- `je_load_density/` - main package
  - `gui/` - PySide6 GUI with multi-language support
  - `utils/` - utilities (executor, file I/O, reports, logging, JSON/XML, socket server, test records)
  - `wrapper/` - Locust wrappers (env creation, event hooks, proxy users, start/stop)
- `load_density_driver/` - driver generation
- `test/` - pytest test suite
- `docs/` - Sphinx documentation

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
