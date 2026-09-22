"""
Allure 2 result writer (no extra dependencies).

Writes JSON files into an output directory in the Allure result format.
Pointing ``allure serve <dir>`` at the directory renders the LoadDensity
run inside any existing Allure dashboard.
"""

import json
import os
import time
import uuid
from typing import Any, Dict, Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance


def _record_to_result(record: Dict[str, Any], outcome: str) -> Dict[str, Any]:
    now_ms = int(time.time() * 1000)
    duration_ms = int(float(record.get("response_time_ms") or 0))
    status = "passed" if outcome == "success" else "failed"
    name = str(record.get("name") or record.get("test_url") or "request")
    test_uuid = str(uuid.uuid4())
    labels = [
        {"name": "suite", "value": "LoadDensity"},
        {"name": "feature", "value": str(record.get("Method") or "")},
    ]
    body: Dict[str, Any] = {
        "uuid": test_uuid,
        "name": name,
        "fullName": f"loaddensity::{name}",
        "status": status,
        "stage": "finished",
        "start": now_ms - duration_ms,
        "stop": now_ms,
        "labels": labels,
        "links": [],
        "steps": [],
        "attachments": [],
        "parameters": [
            {"name": "status_code", "value": str(record.get("status_code", ""))},
            {"name": "response_length",
             "value": str(record.get("response_length", ""))},
        ],
    }
    if outcome == "failure":
        body["statusDetails"] = {
            "message": str(record.get("error") or "request failed"),
        }
    return body


def generate_allure_report(
    output_dir: str = "allure-results",
    label: Optional[str] = None,
) -> str:
    """Write one ``*-result.json`` file per record. Returns the directory path."""
    os.makedirs(output_dir, exist_ok=True)
    if label:
        env_path = os.path.join(output_dir, "environment.properties")
        with open(env_path, "w", encoding="utf-8") as handle:
            handle.write(f"label={label}\n")

    iterations = (
        [(rec, "success") for rec in test_record_instance.test_record_list]
        + [(rec, "failure") for rec in test_record_instance.error_record_list]
    )
    for record, outcome in iterations:
        body = _record_to_result(record, outcome)
        path = os.path.join(output_dir, f"{body['uuid']}-result.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(body, handle, ensure_ascii=False)
    return os.path.abspath(output_dir)
