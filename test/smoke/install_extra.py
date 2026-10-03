"""Install only the selected wheel extra in the Docker cell."""

import re
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Install a declared extra by argument vector and check the resulting environment."""
    extra = sys.argv[1]
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", extra) is None:
        raise ValueError("extra: invalid installation name")
    wheels = list(Path("/wheels").glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("wheel: expected exactly one checkout-built wheel")
    requirement = str(wheels[0]) + (f"[{extra}]" if extra != "base" else "")
    # pywebpush's http-ece dependency publishes source archives; all other dependencies require wheels.
    # Security audit: CI-built wheel path and regex-validated extra are argv data; no shell evaluates them.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-tainted-env-args.dangerous-subprocess-use-tainted-env-args  # noqa: E501
    subprocess.run(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit  # noqa: E501
        [sys.executable, "-m", "pip", "install", "--only-binary", ":all:",
                    "--no-binary", "http-ece", requirement],
                   check=True, timeout=600)
    # Security audit: Current interpreter runs a fixed pip module/command with no shell.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True, timeout=30)
    # Security audit: Current interpreter runs the fixed framework help command with no shell.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
    subprocess.run([sys.executable, "-m", "je_load_density", "--help"], check=True, timeout=30)


if __name__ == "__main__":
    main()
