"""Opt-in canonical recording; legacy imports do not require the new core API."""

try:
    from je_action_core.request_context import RunContext, get_run_context, use_run_context
except ModuleNotFoundError as error:
    if error.name != "je_action_core.request_context":
        raise
    raise RuntimeError(
        "Canonical records require the ActionCore request-record API; upgrade je_action_core "
        "or use the coordinated development checkout."
    ) from error

__all__ = ["RunContext", "get_run_context", "use_run_context"]
