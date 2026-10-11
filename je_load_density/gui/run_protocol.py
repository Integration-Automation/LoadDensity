"""Scheduler independent messages exchanged with the desktop worker."""

import json
from itertools import chain
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from je_load_density.utils.test_record.window_statistics import finite_number, latency_mean, latency_windows, percentile

MAX_RECORDS = 200
MAX_FRAME_BYTES = 131072


def encode_frame(kind: str, **fields: Any) -> str:
    """Retain the newest complete request rows within the reader's UTF-8 byte bound."""
    message = {"type": kind, **fields}
    if kind == "snapshot":
        data = dict(message["data"])
        records = data["records"]
        data["records"] = []
        message["data"] = data
        baseline = json.dumps(message, allow_nan=False) + "\n"
        budget = MAX_FRAME_BYTES - len(baseline.encode("utf-8"))
        retained = []
        for record in reversed(records):
            encoded = json.dumps(record, allow_nan=False)
            cost = len(encoded.encode("utf-8")) + (2 if retained else 0)
            if cost > budget:
                break
            retained.append(record)
            budget -= cost
        data["records"] = list(reversed(retained))
    frame = json.dumps(message, allow_nan=False) + "\n"
    if len(frame.encode("utf-8")) > MAX_FRAME_BYTES:
        raise ValueError("GUI message metadata exceeds the frame byte limit")
    return frame


def safe_name(value: object) -> str:
    """Remove URL credentials, query strings and fragments from display names."""
    text = str(value or "request")
    try:
        parts = urlsplit(text)
        if parts.netloc:
            text = urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, "", ""))
        elif text.startswith(("/", "./", "../")):
            text = parts.path
    except ValueError:
        return "request"
    return text[:500]


def _record(record: dict, failed: bool) -> dict:
    return {"name": safe_name(record.get("name") or record.get("test_url")), "failed": failed,
            "start_time": finite_number(record.get("start_time")),
            "response_time_ms": finite_number(record.get("response_time_ms"))}


def make_snapshot(success: list, failures: list, *, users: int = 0, elapsed: float = 1,
                  start_time: float | None = None, end_time: float | None = None) -> dict:
    """Keep cumulative totals while bounding the transported, credential free request tail."""
    latencies = [value for record in chain(success, failures)
                 if (value := finite_number(record.get("response_time_ms"))) is not None and value >= 0]
    count = len(success) + len(failures)
    summary = {"requests": count, "failures": len(failures), "users": users,
               "rps": count / max(elapsed, 0.001), "failure_rate": len(failures) / max(count, 1),
               "mean_ms": latency_mean(latencies), "p50_ms": percentile(latencies, 50),
               "p95_ms": percentile(latencies, 95), "p99_ms": percentile(latencies, 99)}
    records = [_record(row, False) for row in success[-MAX_RECORDS:]]
    records.extend(_record(row, True) for row in failures[-MAX_RECORDS:])
    records.sort(key=lambda row: row["start_time"] or 0)
    windows = latency_windows(chain(success, failures), start=start_time, end=end_time, max_buckets=120)
    return {"summary": summary, "records": records[-MAX_RECORDS:], "windows": windows}
