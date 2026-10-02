"""Derive isolated Docker installation jobs from the package's declared extras."""

import argparse
import json
import os
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

SUPPORTED_PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13", "3.14")
PR_EXTRAS_PYTHON_VERSION = "3.12"


def build_matrix(metadata_path: Path, scheduled: bool = False) -> dict[str, list[dict[str, str]]]:
    """Cover every declared extra independently; schedules cover every supported Python version."""
    with metadata_path.open("rb") as handle:
        extras = tomllib.load(handle)["project"].get("optional-dependencies", {})
    for name in extras:
        if name == "base" or re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) is None:
            raise ValueError(f"extra: invalid matrix name {name!r}")
    names = ["base", *sorted(extras)]
    versions = SUPPORTED_PYTHON_VERSIONS if scheduled else (PR_EXTRAS_PYTHON_VERSION,)
    cells = [{"python": version, "extra": name} for version in versions for name in names]
    if not scheduled:
        cells.extend({"python": version, "extra": "base"}
                     for version in (SUPPORTED_PYTHON_VERSIONS[0], SUPPORTED_PYTHON_VERSIONS[-1]))
    return {"include": cells}


def main() -> None:
    """Emit JSON for GitHub Actions or a local matrix runner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--event", default="pull_request")
    parser.add_argument("--output", type=Path, default=os.environ.get("GITHUB_OUTPUT"))
    arguments = parser.parse_args()
    payload = json.dumps(build_matrix(arguments.metadata, scheduled=arguments.event == "schedule"))
    if arguments.output is not None:
        with arguments.output.open("a", encoding="utf-8") as handle:
            handle.write(f"matrix={payload}\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
