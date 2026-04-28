import sys
from html import escape
from typing import Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance


def _safe(value: object) -> str:
    return escape(str(value), quote=True)


def generate_junit_report(report_name: str = "loaddensity-junit") -> Optional[str]:
    """
    產生 JUnit XML 報告，供 CI 系統消費。
    Generate a JUnit XML report consumable by CI systems.
    """
    success = test_record_instance.test_record_list
    failures = test_record_instance.error_record_list
    total = len(success) + len(failures)

    parts = []
    parts.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    parts.append(
        f"<testsuite name=\"loaddensity\" tests=\"{total}\" failures=\"{len(failures)}\">"
    )

    for record in success:
        name = _safe(record.get("name") or record.get("test_url"))
        classname = _safe(record.get("Method", "request"))
        time_s = float(record.get("response_time_ms") or 0) / 1000.0
        parts.append(
            f"<testcase classname=\"{classname}\" name=\"{name}\" time=\"{time_s:.3f}\"/>"
        )

    for record in failures:
        name = _safe(record.get("name") or record.get("test_url"))
        classname = _safe(record.get("Method", "request"))
        time_s = float(record.get("response_time_ms") or 0) / 1000.0
        message = _safe(record.get("error") or "request failed")
        parts.append(
            f"<testcase classname=\"{classname}\" name=\"{name}\" time=\"{time_s:.3f}\">"
            f"<failure message=\"{message}\">{message}</failure></testcase>"
        )

    parts.append("</testsuite>")
    xml_body = "".join(parts)

    path = f"{report_name}.xml"
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(xml_body)
        return path
    except OSError as error:
        print(repr(error), file=sys.stderr)
        return None
