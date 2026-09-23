"""
Stateful per-virtual-user cookie jar.

Provides a thread-local store so concurrent Locust users keep their own
cookie state without sharing across users. Built on top of stdlib
``http.cookiejar``.
"""

import threading
from http.cookiejar import CookieJar
from typing import Dict, Optional


_local = threading.local()
_global_jars: Dict[int, CookieJar] = {}
_lock = threading.Lock()


def jar_for_user(user_id: Optional[int] = None) -> CookieJar:
    """Return a CookieJar scoped to ``user_id`` (or current thread)."""
    if user_id is None:
        jar = getattr(_local, "jar", None)
        if jar is None:
            jar = CookieJar()
            _local.jar = jar
        return jar

    with _lock:
        existing = _global_jars.get(user_id)
        if existing is None:
            existing = CookieJar()
            _global_jars[user_id] = existing
        return existing


def reset_user_jar(user_id: Optional[int] = None) -> None:
    """Clear cookies for the given user (or current thread)."""
    if user_id is None:
        if hasattr(_local, "jar"):
            _local.jar.clear()
        return
    with _lock:
        jar = _global_jars.get(user_id)
        if jar is not None:
            jar.clear()


def reset_all_jars() -> None:
    """Drop every cookie jar known to LoadDensity."""
    with _lock:
        for jar in _global_jars.values():
            jar.clear()
        _global_jars.clear()
    if hasattr(_local, "jar"):
        _local.jar.clear()
