"""
Stateful per-virtual-user cookie jar.

Provides a context-local store so concurrent threads, tasks and Locust users
keep their own cookie state. Built on top of stdlib
``http.cookiejar``.
"""

import asyncio
import threading
from contextvars import ContextVar
from http.cookiejar import CookieJar
from typing import Dict, Optional, Tuple

_CookieOwner = Tuple[int, Optional[int]]
_local: ContextVar[Optional[Tuple[_CookieOwner, CookieJar]]] = ContextVar("load_density_cookie_jar", default=None)
_global_jars: Dict[int, CookieJar] = {}
_lock = threading.Lock()


def jar_for_user(user_id: Optional[int] = None) -> CookieJar:
    """Return a CookieJar scoped to ``user_id`` or the current execution context."""
    if user_id is None:
        owner = _current_owner()
        selected = _local.get()
        if selected is None or selected[0] != owner:
            selected = (owner, CookieJar())
            _local.set(selected)
        return selected[1]

    with _lock:
        existing = _global_jars.get(user_id)
        if existing is None:
            existing = CookieJar()
            _global_jars[user_id] = existing
        return existing


def _current_owner() -> _CookieOwner:
    """Detach inherited task contexts while keeping thread and greenlet isolation."""
    try:
        current_task = asyncio.current_task()
    except RuntimeError:
        current_task = None
    return threading.get_ident(), None if current_task is None else id(current_task)


def _clear_current_jar() -> None:
    selected = _local.get()
    if selected is not None and selected[0] == _current_owner():
        selected[1].clear()


def reset_user_jar(user_id: Optional[int] = None) -> None:
    """Clear cookies for the given user or the current execution context."""
    if user_id is None:
        _clear_current_jar()
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
    _clear_current_jar()
