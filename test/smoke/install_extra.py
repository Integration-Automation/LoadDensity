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
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary", ":all:", requirement],
                   check=True, timeout=600)
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True, timeout=30)
    subprocess.run([sys.executable, "-m", "je_load_density", "--help"], check=True, timeout=30)


if __name__ == "__main__":
    main()
