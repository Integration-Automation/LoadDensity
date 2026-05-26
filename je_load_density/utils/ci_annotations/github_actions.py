"""
GitHub Actions ``::error::`` / ``::warning::`` annotation emitter.

Renders one workflow-command line per failed request so reviewers see
inline failures in the PR ``Files Changed`` view.
"""

import sys
from typing import Iterable, Iterator, List, Optional, TextIO

from je_load_density.utils.test_record.test_record_class import test_record_instance


def format_github_annotation(
    severity: str,
    message: str,
    file: Optional[str] = None,
    line: Optional[int] = None,
    title: Optional[str] = None,
) -> str:
    """
    Build one ``::<severity> [opts]::message`` line.

    severity must be ``error``, ``warning``, or ``notice``.
    """
    if severity not in {"error", "warning", "notice"}:
        raise ValueError(f"unsupported severity: {severity!r}")

    options: List[str] = []
    if file:
        options.append(f"file={_escape(file)}")
    if line is not None:
        options.append(f"line={int(line)}")
    if title:
        options.append(f"title={_escape(title)}")

    option_str = f" {','.join(options)}" if options else ""
    return f"::{severity}{option_str}::{_escape_message(message)}"


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace(",", "%2C").replace(":", "%3A")


def _escape_message(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _iter_failure_annotations(records: Iterable[dict],
                              title: str) -> Iterator[str]:
    for record in records:
        url = record.get("test_url") or record.get("name") or "(unknown)"
        method = record.get("Method") or record.get("method") or ""
        status = record.get("status_code")
        error = record.get("error") or "request failed"
        suffix = f" (HTTP {status})" if status else ""
        message = f"{method} {url}{suffix}: {error}"
        yield format_github_annotation("error", message, title=title)


def emit_github_annotations(
    title: str = "LoadDensity",
    stream: Optional[TextIO] = None,
) -> int:
    """
    Print one ``::error::`` annotation per failure record. Returns the
    number of annotations written.
    """
    out = stream if stream is not None else sys.stdout
    written = 0
    for line in _iter_failure_annotations(test_record_instance.error_record_list, title):
        out.write(line + "\n")
        written += 1
    return written
