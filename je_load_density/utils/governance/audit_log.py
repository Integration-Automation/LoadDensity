"""
Append-only audit log for LoadDensity actions.

Writes JSONL entries to a file (or any writable handle). Each entry
records who did what when, intended for compliance trails when running
LoadDensity inside enterprise environments.
"""

import json
import os
import threading
import time
from typing import Any, Dict, Optional


_lock = threading.Lock()


def append_audit_entry(
    log_path: str,
    action: str,
    user: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a single audit entry to ``log_path`` (creates if missing)."""
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user": user or os.environ.get("LD_AUDIT_USER", "anonymous"),
        "action": action,
        "details": details or {},
    }
    with _lock:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_audit_log(log_path: str) -> list:
    """Return every audit entry as a list of dicts."""
    if not os.path.isfile(log_path):
        return []
    entries = []
    with open(log_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries
