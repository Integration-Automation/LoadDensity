import csv
import sys
from typing import Iterable, List, Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance

_FIELDS: List[str] = [
    "outcome",
    "Method",
    "test_url",
    "name",
    "status_code",
    "response_time_ms",
    "response_length",
    "error",
]


def _rows() -> Iterable[dict]:
    for record in test_record_instance.test_record_list:
        row = {key: record.get(key) for key in _FIELDS}
        row["outcome"] = "success"
        yield row
    for record in test_record_instance.error_record_list:
        row = {key: record.get(key) for key in _FIELDS}
        row["outcome"] = "failure"
        yield row


def generate_csv_report(csv_name: str = "default_name") -> Optional[str]:
    """
    產生 CSV 報告。
    Generate a CSV report containing both success and failure records.
    Returns the path written, or None on failure.
    """
    csv_path = f"{csv_name}.csv"
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS)
            writer.writeheader()
            for row in _rows():
                writer.writerow(row)
        return csv_path
    except OSError as error:
        print(repr(error), file=sys.stderr)
        return None
