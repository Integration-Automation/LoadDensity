"""
Performance regression root-cause prompt builder.

Combines:
- ``diff_runs`` output (baseline vs current)
- ``cluster_errors`` output (which errors dominate)
- A short git diff stat (if available)

into a single prompt-ready dict the caller can hand to any LLM API
(Claude, OpenAI, local Ollama, etc). This module *does not* call any
LLM itself — it just builds the structured context.
"""

import shutil
import subprocess  # nosec - git invocation is intentional
from typing import Any, Dict, List, Optional


def _git_diff_stat(commits: int = 5, timeout: float = 5.0) -> Optional[str]:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        completed = subprocess.run(  # nosec B603  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
            [git, "log", "--stat", f"-{commits}"],
            capture_output=True, timeout=timeout, check=False,
        )
        if completed.returncode != 0:
            return None
        return completed.stdout.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None


def build_root_cause_prompt(
    diff_report: Dict[str, Any],
    error_clusters: List[Dict[str, Any]],
    summary: Dict[str, Any],
    extra_context: Optional[str] = None,
    include_git_log: bool = True,
) -> Dict[str, Any]:
    """Build a structured prompt-ready context dict."""
    git_log = _git_diff_stat() if include_git_log else None
    return {
        "task": (
            "Analyze the LoadDensity performance regression below. "
            "Identify the most likely root cause(s), referencing the "
            "endpoints, error clusters, and recent commits."
        ),
        "summary": summary,
        "diff_report": diff_report,
        "top_error_clusters": error_clusters[:5],
        "recent_git_log": git_log,
        "extra_context": extra_context,
    }


def render_prompt_text(context: Dict[str, Any]) -> str:
    """Render the prompt context as plain text suitable for LLM input."""
    import json
    return (
        f"{context['task']}\n\n"
        f"## Summary\n```json\n{json.dumps(context['summary'], indent=2)}\n```\n\n"
        f"## Regression diff (baseline vs current)\n```json\n"
        f"{json.dumps(context['diff_report'], indent=2)}\n```\n\n"
        f"## Top error clusters\n```json\n"
        f"{json.dumps(context['top_error_clusters'], indent=2)}\n```\n\n"
        f"## Recent git log\n```\n{context.get('recent_git_log') or '(none)'}\n```\n\n"
        f"## Extra context\n{context.get('extra_context') or '(none)'}\n"
    )
