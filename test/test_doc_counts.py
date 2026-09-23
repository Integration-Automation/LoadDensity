"""The counts quoted in the docs must match the code.

Counts in prose drift: CLAUDE.md said "HTTP and 29 other protocols" long after the user registry had
grown to 41 entries. Each row below names a document, a pattern with one number in it, and how to
measure that number. A failure means either the number moved and the document was not updated, or
the sentence was reworded and the pattern here has to follow it; the message says which.
"""
import pathlib
import re
from typing import Callable, List, Tuple

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _mcp_tools() -> int:
    from je_load_density.mcp_server import server
    return len(server._TOOLS)


def _user_types() -> int:
    from je_load_density.wrapper.start_wrapper.start_test import _USER_REGISTRY
    return len(_USER_REGISTRY)


def _safe_builtins() -> int:
    from je_load_density.utils.executor.action_executor import SAFE_BUILTINS
    return len(SAFE_BUILTINS)


def _examples() -> int:
    return sum(1 for path in (ROOT / "examples").iterdir() if path.is_file() and path.name != "README.md")


# (document, regex with one capture group, what it counts, how to measure it)
CITATIONS: List[Tuple[str, str, str, Callable[[], int]]] = [
    ("README.md", r"exposes (\d+) tools", "MCP tools", _mcp_tools),
    ("README.md", r"# MCP server \((\d+) tools", "MCP tools", _mcp_tools),
    ("README.md", r"ships (\d+) runnable recipes", "examples", _examples),
    ("CLAUDE.md", r"user templates for (\d+) user types", "user types in _USER_REGISTRY", _user_types),
    ("architecture.md", r"`SAFE_BUILTINS`, (\d+) names", "SAFE_BUILTINS", _safe_builtins),
]


@pytest.mark.parametrize("document, pattern, label, measure", CITATIONS,
                         ids=[f"{doc}:{label}" for doc, _, label, _ in CITATIONS])
def test_quoted_count_matches_the_code(document, pattern, label, measure):
    text = (ROOT / document).read_text(encoding="utf-8")
    quoted = [int(number) for number in re.findall(pattern, text)]
    assert quoted, f"{document}: no sentence matches {pattern!r} any more; update the pattern to the new wording"
    actual = measure()
    assert all(number == actual for number in quoted), (
        f"{document} quotes {quoted} {label}, the code has {actual}: update the document")
