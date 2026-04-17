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

### Git Commit Rules

- Commit messages must NOT reference any AI tool, assistant, or model name
- No `Co-Authored-By` lines referencing AI
- Write commit messages as if authored solely by the developer
- Use conventional commit style: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- Keep subject line under 72 characters
- Use imperative mood ("add feature" not "added feature")
