"""
Lightweight test-data factory.

Mirrors the factory_boy style but uses stdlib + secrets so it ships
with zero extra deps. Lets a load test materialise N synthetic users in
one call.
"""

import secrets
import string
from typing import Any, Callable, Dict, List, Optional


def _email(prefix: str = "user") -> str:
    return f"{prefix}_{secrets.token_hex(4)}@example.test"


def _username(prefix: str = "user") -> str:
    return f"{prefix}_{secrets.token_hex(3)}"


def _password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


_DEFAULT_BUILDERS: Dict[str, Callable[[], Any]] = {
    "email": _email,
    "username": _username,
    "password": lambda: _password(),
    "uuid_hex": lambda: secrets.token_hex(16),
    "int_id": lambda: secrets.randbits(31),
}


def build_user(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a single synthetic user dict."""
    user = {key: builder() for key, builder in _DEFAULT_BUILDERS.items()}
    user.update(overrides or {})
    return user


def build_user_pool(
    count: int,
    overrides: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Build ``count`` synthetic users, each with stable independent values."""
    return [build_user(overrides) for _ in range(max(0, count))]
