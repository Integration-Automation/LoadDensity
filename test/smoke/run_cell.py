"""Run installation capability checks and full wheel smoke tests with bounded child processes."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Keep capability results separate from the base runtime smoke result."""
    directory = Path(__file__).resolve().parent
    # Security audit: Fixed sibling script receives LD_EXTRA as one argv value; its probe registry rejects unknown
    # names.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-tainted-env-args.dangerous-subprocess-use-tainted-env-args  # noqa: E501
    subprocess.run(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit  # noqa: E501
        [sys.executable, str(directory / "capability_probe.py"), os.environ.get("LD_EXTRA", "base")],
                   check=True, timeout=120)
    # Security audit: Current interpreter runs the fixed sibling smoke script with no shell.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
    subprocess.run([sys.executable, str(directory / "test_wheel_smoke.py"), "-v"], check=True, timeout=240)


if __name__ == "__main__":
    main()
