"""
SARIF 2.1.0 report writer.

Translates LoadDensity failures into SARIF results so they can land in
GitHub code scanning, GitLab security dashboards, or SonarQube.
"""

import json
import os
from typing import Any, Dict, List, Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance


def _result_for(record: Dict[str, Any]) -> Dict[str, Any]:
    name = str(record.get("name") or record.get("test_url") or "request")
    message = str(record.get("error") or record.get("status_code") or "request failed")
    return {
        "ruleId": "LD0001",
        "level": "error",
        "message": {"text": f"{name}: {message}"},
        "locations": [{
            "physicalLocation": {
                "artifactLocation": {"uri": name},
            },
        }],
        "properties": {
            "method": record.get("Method", ""),
            "status_code": record.get("status_code", ""),
            "response_time_ms": record.get("response_time_ms", 0),
        },
    }


def generate_sarif_report(
    report_name: str = "loaddensity-sarif",
    tool_version: str = "1.0",
    extra_records: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Write a SARIF 2.1.0 file. Returns its path."""
    failures = list(test_record_instance.error_record_list)
    if extra_records:
        failures.extend(extra_records)
    document: Dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
                    "master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "LoadDensity",
                    "informationUri": "https://loaddensity.readthedocs.io",
                    "version": tool_version,
                    "rules": [{
                        "id": "LD0001",
                        "name": "RequestFailure",
                        "shortDescription": {"text": "Load-test request failed"},
                        "defaultConfiguration": {"level": "error"},
                    }],
                },
            },
            "results": [_result_for(record) for record in failures],
        }],
    }
    file_path = f"{report_name}.sarif.json"
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
    return os.path.abspath(file_path)
