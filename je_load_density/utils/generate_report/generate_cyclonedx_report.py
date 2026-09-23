"""
CycloneDX 1.5 SBOM writer for the LoadDensity install footprint.

Lists every importable Python distribution (via ``importlib.metadata``)
so security tooling can ingest the run-time dependencies of the host
process.
"""

import json
import os
import uuid
from importlib.metadata import distributions
from typing import Any, Dict, List


def _component(distribution) -> Dict[str, Any]:
    name = distribution.metadata.get("Name", "unknown")
    version = distribution.version or "0.0"
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name}@{version}",
        "licenses": [{"license": {"name": distribution.metadata.get("License", "UNKNOWN")}}],
    }


def generate_cyclonedx_report(
    report_name: str = "loaddensity-sbom",
) -> str:
    """Emit a CycloneDX 1.5 SBOM JSON. Returns the path."""
    components: List[Dict[str, Any]] = []
    seen = set()
    for distribution in distributions():
        name = distribution.metadata.get("Name", "")
        if not name or name in seen:
            continue
        seen.add(name)
        components.append(_component(distribution))

    document: Dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "tools": [{"vendor": "loaddensity", "name": "sbom-writer", "version": "1.0"}],
            "component": {
                "type": "application",
                "name": "loaddensity-runtime",
                "version": "1.0",
            },
        },
        "components": components,
    }
    file_path = f"{report_name}.cdx.json"
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
    return os.path.abspath(file_path)
