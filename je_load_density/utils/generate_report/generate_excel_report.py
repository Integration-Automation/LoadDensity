"""
Excel (XLSX) report writer.

Stdlib-only — builds the minimum-viable ``.xlsx`` (OOXML) zip by hand
so the report does NOT require openpyxl. Writes a single "Records"
sheet containing every test record.
"""

import os
import xml.sax.saxutils as xml_escape
import zipfile
from typing import Any, Dict, Iterable, List, Optional

from je_load_density.utils.test_record.test_record_class import test_record_instance

_COLUMNS = (
    "outcome", "Method", "name", "test_url", "status_code",
    "response_time_ms", "response_length", "error",
)


def _cell(value: Any, column_index: int) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{_column_ref(column_index)}"><v>{value}</v></c>'
    escaped = xml_escape.escape("" if value is None else str(value))
    return (
        f'<c r="{_column_ref(column_index)}" t="inlineStr">'
        f"<is><t>{escaped}</t></is></c>"
    )


def _column_ref(index: int) -> str:
    # 0 -> A, 25 -> Z, 26 -> AA, ...
    letters = ""
    cursor = index
    while True:
        letters = chr(ord("A") + cursor % 26) + letters
        cursor = cursor // 26 - 1
        if cursor < 0:
            break
    return letters


def _row(values: List[Any], row_index: int) -> str:
    cells = "".join(_cell(value, i) for i, value in enumerate(values))
    return f'<row r="{row_index + 1}">{cells}</row>'


def _sheet_xml(rows: Iterable[List[Any]]) -> bytes:
    rendered_rows = "".join(_row(row, i) for i, row in enumerate(rows))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{rendered_rows}</sheetData>"
        "</worksheet>"
    ).encode("utf-8")


_WORKBOOK_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="Records" sheetId="1" r:id="rId1"/></sheets>'
    "</workbook>"
).encode("utf-8")

_WORKBOOK_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
    '2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    "</Relationships>"
).encode("utf-8")

_ROOT_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
    '2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
).encode("utf-8")

_CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
    'relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.'
    'openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    "</Types>"
).encode("utf-8")


def _build_rows(records: Iterable[Dict[str, Any]], outcome_label: str) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for record in records:
        row = [outcome_label]
        for column in _COLUMNS[1:]:
            row.append(record.get(column))
        rows.append(row)
    return rows


def generate_excel_report(
    report_name: str = "loaddensity-records",
    extra_label: Optional[str] = None,
) -> str:
    """Write an XLSX file containing every test record. Returns its path."""
    header_row = [list(_COLUMNS)]
    success_rows = _build_rows(test_record_instance.test_record_list, "success")
    failure_rows = _build_rows(test_record_instance.error_record_list, "failure")
    sheet_bytes = _sheet_xml(header_row + success_rows + failure_rows)

    file_path = f"{report_name}.xlsx"
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
        archive.writestr("_rels/.rels", _ROOT_RELS_XML)
        archive.writestr("xl/workbook.xml", _WORKBOOK_XML)
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS_XML)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_bytes)
        if extra_label:
            archive.writestr("docProps/loaddensity.txt", extra_label.encode("utf-8"))
    return os.path.abspath(file_path)
