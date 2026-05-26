"""
Network conditioner.

Per-task latency / jitter / packet-loss injector implemented inside the
scenario runner, so it works against every user template uniformly
(no kernel ``tc`` required). Drops are simulated by raising a
``ConnectionError`` before the request fires.
"""

import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class NetworkConditioner:
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    loss_rate: float = 0.0
    name_filter: Optional[str] = None

    def applies_to(self, task: Dict[str, Any]) -> bool:
        if self.name_filter is None:
            return True
        return self.name_filter in str(task.get("name") or task.get("request_url") or "")

    def _sample_latency_ms(self) -> float:
        if self.jitter_ms <= 0:
            return max(0.0, self.latency_ms)
        span_us = max(1, int(self.jitter_ms * 1000))
        spread = secrets.randbelow(span_us * 2) / 1000.0 - self.jitter_ms
        return max(0.0, self.latency_ms + spread)

    def _should_drop(self) -> bool:
        if self.loss_rate <= 0:
            return False
        if self.loss_rate >= 1:
            return True
        ratio = secrets.randbelow(10_000) / 10_000.0
        return ratio < self.loss_rate

    def apply(self, task: Dict[str, Any], sleeper: Callable[[float], None] = time.sleep) -> None:
        if not self.applies_to(task):
            return
        if self._should_drop():
            raise ConnectionError(f"network_conditioner: simulated drop ({self.loss_rate})")
        delay_seconds = self._sample_latency_ms() / 1000.0
        if delay_seconds > 0:
            sleeper(delay_seconds)


_INSTALLED: Optional[NetworkConditioner] = None


def install_network_conditioner(
    latency_ms: float = 0.0,
    jitter_ms: float = 0.0,
    loss_rate: float = 0.0,
    name_filter: Optional[str] = None,
) -> NetworkConditioner:
    global _INSTALLED
    _INSTALLED = NetworkConditioner(latency_ms=latency_ms,
                                    jitter_ms=jitter_ms,
                                    loss_rate=loss_rate,
                                    name_filter=name_filter)
    return _INSTALLED


def uninstall_network_conditioner() -> None:
    global _INSTALLED
    _INSTALLED = None


def current_conditioner() -> Optional[NetworkConditioner]:
    return _INSTALLED
