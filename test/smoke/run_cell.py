"""Run installation capability checks and full wheel smoke tests with bounded child processes."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Keep capability results separate from the base runtime smoke result."""
    directory = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(directory / "capability_probe.py"), os.environ.get("LD_EXTRA", "base")],
                   check=True, timeout=120)
    subprocess.run([sys.executable, str(directory / "test_wheel_smoke.py"), "-v"], check=True, timeout=240)


if __name__ == "__main__":
    main()
