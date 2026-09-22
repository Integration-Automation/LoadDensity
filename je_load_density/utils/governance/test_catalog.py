"""
Test catalog — index of shared action JSON documents.

Scans one or more directories for ``*.json`` files, parses them as
action documents, and produces a searchable index keyed by tag /
owner / name.
"""

import json
import os
from typing import Any, Dict, Iterable, List, Optional


def _read_doc(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _walk(directory: str) -> Iterable[str]:
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if name.endswith(".json"):
                yield os.path.join(root, name)


def index_catalog(directories: List[str]) -> List[Dict[str, Any]]:
    """Index every ``*.json`` under each directory. Returns metadata rows."""
    entries: List[Dict[str, Any]] = []
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        for path in _walk(directory):
            doc = _read_doc(path)
            if doc is None:
                continue
            metadata = doc.get("metadata") or {} if isinstance(doc, dict) else {}
            entries.append({
                "path": path,
                "name": metadata.get("name") or os.path.basename(path),
                "owner": metadata.get("owner") or "",
                "tags": list(metadata.get("tags") or []),
                "description": metadata.get("description") or "",
            })
    return entries


def search_catalog(
    entries: List[Dict[str, Any]],
    tag: Optional[str] = None,
    owner: Optional[str] = None,
    text: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter the catalog by tag / owner / free-text."""
    results = entries
    if tag:
        results = [entry for entry in results if tag in entry["tags"]]
    if owner:
        results = [entry for entry in results if entry["owner"] == owner]
    if text:
        needle = text.lower()
        results = [
            entry for entry in results
            if needle in entry["name"].lower() or needle in entry["description"].lower()
        ]
    return results
