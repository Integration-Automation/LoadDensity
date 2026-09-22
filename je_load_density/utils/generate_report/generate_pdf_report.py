"""
PDF summary report (reportlab, lazy import).

Renders the build_summary output as a one-page printable PDF.
"""

import os
from typing import Any, Dict, Optional


class PdfDependencyError(RuntimeError):
    """Raised when reportlab is not installed."""


def _import_reportlab():
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib import colors
    except ImportError as error:
        raise PdfDependencyError(
            "reportlab is required for PDF reports. "
            "Install with: pip install reportlab"
        ) from error
    return {
        "letter": letter,
        "styles": getSampleStyleSheet,
        "Paragraph": Paragraph,
        "SimpleDocTemplate": SimpleDocTemplate,
        "Spacer": Spacer,
        "Table": Table,
        "TableStyle": TableStyle,
        "colors": colors,
    }


def _totals_table(rl, summary: Dict[str, Any]):
    totals = summary.get("totals", {})
    latency = summary.get("latency_overall", {})
    data = [
        ["Metric", "Value"],
        ["Requests", str(totals.get("requests", 0))],
        ["Failures", str(totals.get("failures", 0))],
        ["Failure rate", f"{totals.get('failure_rate', 0):.2%}"],
        ["P50 ms", f"{latency.get('p50_ms', 0):.1f}"],
        ["P95 ms", f"{latency.get('p95_ms', 0):.1f}"],
        ["P99 ms", f"{latency.get('p99_ms', 0):.1f}"],
    ]
    table = rl["Table"](data, hAlign="LEFT", colWidths=[180, 120])
    table.setStyle(rl["TableStyle"]([
        ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl["colors"].whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.25, rl["colors"].black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    return table


def generate_pdf_report(
    report_name: str = "loaddensity-summary",
    summary: Optional[Dict[str, Any]] = None,
    title: str = "LoadDensity run",
) -> str:
    """Render a one-page PDF and return its absolute path."""
    rl = _import_reportlab()
    if summary is None:
        from je_load_density.utils.generate_report.generate_summary_report import (
            build_summary,
        )
        summary = build_summary()

    file_path = f"{report_name}.pdf"
    document = rl["SimpleDocTemplate"](file_path, pagesize=rl["letter"])
    styles = rl["styles"]()
    flow = [
        rl["Paragraph"](title, styles["Title"]),
        rl["Spacer"](1, 12),
        _totals_table(rl, summary),
    ]
    document.build(flow)
    return os.path.abspath(file_path)
