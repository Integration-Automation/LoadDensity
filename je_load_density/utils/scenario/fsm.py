"""
Finite state machine scenario runner.

Given a task list whose entries declare ``state`` + ``transitions``, the
FSM picks the next task based on the most recent task's outcome (status,
extracted variables, etc.). This complements the existing
``sequence`` / ``weighted`` / ``conditional`` scenario modes by letting
authors express stateful flows (login → browse → checkout → retry) in
JSON.

Each task entry::

    {"state": "login", ...payload..., "transitions": {
        "success": "browse",
        "failure": "retry_login",
        "default": "browse"
    }}

The runner is intentionally pure — it does not execute tasks; it only
returns the next state given (current_state, outcome). The host user
template owns request firing.
"""

from typing import Any, Dict, List, Optional


class FsmRunner:
    """Stateless next-state selector for FSM scenarios."""

    def __init__(self, tasks: List[Dict[str, Any]]) -> None:
        self._tasks_by_state: Dict[str, Dict[str, Any]] = {}
        self._initial: Optional[str] = None
        for task in tasks:
            state = str(task.get("state", "") or "")
            if not state:
                continue
            self._tasks_by_state[state] = task
            if self._initial is None:
                self._initial = state

    @property
    def initial_state(self) -> Optional[str]:
        return self._initial

    def task_for(self, state: str) -> Optional[Dict[str, Any]]:
        return self._tasks_by_state.get(state)

    def next_state(self, current_state: str, outcome: str) -> Optional[str]:
        task = self._tasks_by_state.get(current_state)
        if task is None:
            return None
        transitions = task.get("transitions") or {}
        if not isinstance(transitions, dict):
            return None
        target = transitions.get(outcome) or transitions.get("default")
        if target == current_state:
            return None
        return target

    def run(
        self,
        executor,
        max_steps: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Drive the FSM until a terminal state or ``max_steps``.

        ``executor`` is a callable that takes the task dict and returns
        a string outcome (typically ``"success"`` / ``"failure"``).
        """
        history: List[Dict[str, Any]] = []
        state = self._initial
        for _ in range(max_steps):
            if state is None:
                break
            task = self._tasks_by_state.get(state)
            if task is None:
                break
            outcome = executor(task)
            history.append({"state": state, "outcome": outcome})
            state = self.next_state(state, str(outcome))
        return history
