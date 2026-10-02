"""Shared preflight validation and partial launch evidence for cloud adapters."""

import math
from typing import Any, Dict, List, Optional, Tuple, Type


class CloudLaunchError(RuntimeError):
    """A failed launch with prior accepted responses; never implies rollback.

    ``failed_workers`` contains worker indices. ``responses`` contains successful
    or accepted responses in worker order, so callers can inspect existing work
    before deciding whether to launch replacements. ``response`` holds the failed
    service response when available. SDK errors are preserved as exception causes.
    """

    def __init__(self, backend: str, failed_workers: List[int], responses: List[Dict[str, Any]],
                 message: str, response: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(f"{backend}: {message}; failed workers {failed_workers}")
        self.backend = backend
        self.failed_workers = list(failed_workers)
        self.responses = list(responses)
        self.response = response


def positive_integer(value: int, name: str) -> None:
    """Require an actual positive integer, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def positive_number(value: float, name: str) -> None:
    """Require a positive finite numeric resource or timeout value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")


def required_string(value: str, name: str) -> None:
    """Require a nonblank string without embedded null characters."""
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"{name} must be a nonempty string")


def validate_environment(environment: Optional[Dict[str, str]]) -> None:
    """Validate string environment values and reserved worker identity names."""
    if environment is None:
        return
    if not isinstance(environment, dict):
        raise ValueError("overrides_env must be a dictionary of strings")
    for name, value in environment.items():
        required_string(name, "environment name")
        if name in {"LD_WORKER_INDEX", "LD_WORKER_COUNT"}:
            raise ValueError(f"{name} is reserved for worker identity")
        if not isinstance(value, str) or "\x00" in value:
            raise ValueError("environment values must be strings without null characters")


def sdk_error_types(provider: str) -> Tuple[Type[Exception], ...]:
    """Return optional SDK base errors without requiring SDKs for module import."""
    try:
        if provider == "aws":
            from botocore.exceptions import BotoCoreError, ClientError
            return (BotoCoreError, ClientError, OSError)
        from azure.core.exceptions import AzureError
        return (AzureError, OSError)
    except ImportError:
        # Lightweight SDK doubles need only the standard transport boundary.
        return (OSError,)
