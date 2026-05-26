"""
CLI entry point used by the pre-commit hook.

Reads every action JSON path on the command line, runs the linter, and
prints findings. Exits non-zero if any error-level finding shows up.
"""

import os
import sys
from typing import List

from je_load_density.utils.linter.action_linter import lint_action_file


def main(argv: List[str]) -> int:
    files = argv[1:]
    if not files:
        return 0

    had_error = False
    for path in files:
        if not os.path.exists(path):
            continue
        try:
            findings = lint_action_file(path)
        except Exception as error:
            print(f"{path}: failed to parse ({error!r})", file=sys.stderr)
            had_error = True
            continue
        for finding in findings:
            sev = finding["severity"].upper()
            print(f"{path}: [{sev}] {finding['rule']}: {finding['message']}",
                  file=sys.stderr)
            if finding["severity"] == "error":
                had_error = True
    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
