"""Observe Locust worker health without sending heartbeats or assigning virtual users."""
from enum import Enum

import gevent
from locust.env import Environment
from locust.runners import WorkerNode

from .distributed_config import DistributedConfig


class WorkerState(str, Enum):
    """Public worker lifecycle states."""

    CONNECTING = "connecting"
    READY = "ready"
    RUNNING = "running"
    LOST = "lost"
    STOPPED = "stopped"


class DistributedHealth:
    """Observe native missing/reconnection state and disclose affected stateful journeys."""

    def __init__(self, environment: Environment, config: DistributedConfig) -> None:
        self.environment = environment
        self.config = config
        self.status = "connecting"
        self.reason: str | None = None
        self.workers: dict[str, WorkerState] = {}
        self.affected_workers: set[str] = set()
        self._started = False
        self._closed = False
        self._required_workers = config.expected_workers
        self._listeners = [
            (environment.events.worker_connect, self._connecting),
            (environment.events.test_start, self._start),
            (environment.events.test_stop, self._stop),
        ]
        for hook, listener in self._listeners:
            hook.add_listener(listener)

    @property
    def ready_count(self) -> int:
        """Count only ready clients with an unexpired native heartbeat lease."""
        return sum(client.state == "ready" and client.heartbeat >= 0
                   for client in self.environment.runner.clients.all)

    def _connecting(self, client_id: str, **_kwargs) -> None:
        self.workers[client_id] = WorkerState.CONNECTING

    def _start(self, **_kwargs) -> None:
        self._started = True
        if self.status != "degraded":
            self.status = "running"

    def _stop(self, **_kwargs) -> None:
        self.refresh()
        if self.status not in ("failed", "degraded"):
            self.status = "stopped"

    def degraded_startup(self, expected_workers: int, reason: str) -> None:
        """Retain an explicitly accepted startup shortfall in the final report."""
        self._required_workers = expected_workers
        self.status = "degraded"
        self.reason = reason

    def fail(self, reason: str) -> None:
        """Record an infrastructure failure independently of target request errors."""
        self.status = "failed"
        self.reason = reason
        self.environment.process_exit_code = 1

    def refresh(self) -> None:
        """Read native state; preserve loss history while allowing native reconnection."""
        if self._closed:
            return
        runner = self.environment.runner
        present = set()
        healthy = 0
        for client in runner.clients.all:
            present.add(client.id)
            state = self._worker_state(client)
            self.workers[client.id] = state
            if state == WorkerState.LOST:
                self.affected_workers.add(client.id)
            healthy += state in (WorkerState.READY, WorkerState.RUNNING)
        for worker_id in self.workers.keys() - present:
            self.workers[worker_id] = WorkerState.STOPPED
            if self._started:
                self.affected_workers.add(worker_id)
        self._update_status(healthy)

    @staticmethod
    def _worker_state(client: WorkerNode) -> WorkerState:
        if client.state == "missing":
            return WorkerState.LOST
        if client.state in ("running", "spawning"):
            return WorkerState.RUNNING
        if client.state == "ready":
            return WorkerState.READY
        return WorkerState.STOPPED

    def _update_status(self, healthy: int) -> None:
        runner = self.environment.runner
        if self.status in ("failed", "stopped"):
            return
        if not self._started:
            self.status = "ready" if self.ready_count else "connecting"
            return
        if not healthy:
            self.fail("all workers lost or stopped")
            return
        insufficient = runner.user_count < runner.target_user_count and runner.spawning_completed
        if healthy < self._required_workers or insufficient or runner.worker_cpu_warning_emitted:
            self.status = "degraded"
            self.reason = "worker availability or observed capacity below the requested load"
        else:
            self.status = "running"
            self.reason = None

    def monitor(self) -> None:
        """Poll native state only; quit when no worker can deliver the load."""
        while not self._closed:
            self.refresh()
            if self.status == "failed":
                self.environment.runner.quit()
                return
            gevent.sleep(min(self.config.heartbeat_interval, 0.1))

    def snapshot(self) -> dict[str, object]:
        """Return serializable health, capacity and session-continuity disclosure."""
        self.refresh()
        runner = self.environment.runner
        return {"status": self.status, "reason": self.reason,
                "workers": {key: state.value for key, state in self.workers.items()},
                "target_users": runner.target_user_count, "reported_users": runner.user_count,
                "affected_workers": sorted(self.affected_workers),
                "session_continuity": "not guaranteed", "request_replay": False}

    def close(self) -> None:
        """Detach health listeners while preserving the final run health snapshot."""
        self.refresh()
        if self.status not in ("failed", "degraded"):
            self.status = "stopped"
        self._closed = True
        for worker_id in self.workers:
            self.workers[worker_id] = WorkerState.STOPPED
        for hook, listener in self._listeners:
            hook.remove_listener(listener)
