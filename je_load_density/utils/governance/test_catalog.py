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


def _metadata_of(doc: Any) -> Dict[str, Any]:
    """The document's ``metadata`` mapping, or ``{}`` when it is missing or not a mapping."""
    metadata = doc.get("metadata") if isinstance(doc, dict) else None
    return metadata if isinstance(metadata, dict) else {}


def _tags_of(metadata: Dict[str, Any]) -> List[str]:
    """``tags`` as a list of strings; a single string is one tag, not a list of characters."""
    tags = metadata.get("tags")
    if isinstance(tags, str):
        return [tags]
    if isinstance(tags, list):
        return [str(tag) for tag in tags]
    return []


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
            metadata = _metadata_of(doc)
            entries.append({
                "path": path,
                "name": metadata.get("name") or os.path.basename(path),
                "owner": metadata.get("owner") or "",
                "tags": _tags_of(metadata),
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
