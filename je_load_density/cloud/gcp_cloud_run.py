"""
Google Cloud Run Jobs ephemeral worker adapter.

Uses the Cloud Run Admin v2 REST API directly via a Google-issued bearer
token (so the only third-party dep is ``google-auth``). Submits N
parallel executions of a pre-deployed Cloud Run Job.
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def _import_google_auth():
    try:
        import google.auth
        import google.auth.transport.requests as gauth_requests
    except ImportError as error:
        raise RuntimeError(
            "google-auth is required for the Cloud Run adapter; "
            "install with: pip install google-auth"
        ) from error
    return google.auth, gauth_requests


def _bearer_token(scopes: List[str]) -> str:
    google_auth, gauth_requests = _import_google_auth()
    credentials, _project = google_auth.default(scopes=scopes)
    credentials.refresh(gauth_requests.Request())
    return credentials.token


def run_cloud_run_job(
    project: str,
    region: str,
    job_name: str,
    parallelism: Optional[int] = None,
    task_count: Optional[int] = None,
    container_overrides: Optional[List[Dict[str, Any]]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Trigger a Cloud Run Job execution. Returns the API response JSON."""
    token = _bearer_token(["https://www.googleapis.com/auth/cloud-platform"])
    # Each name is one path segment; quoting keeps a stray "/" or "?" from addressing another resource.
    project, region, job_name = (urllib.parse.quote(str(part), safe="") for part in (project, region, job_name))
    url = (
        f"https://run.googleapis.com/v2/projects/{project}/locations/"
        f"{region}/jobs/{job_name}:run"
    )
    body: Dict[str, Any] = {"overrides": {}}
    if parallelism is not None:
        body["overrides"]["parallelism"] = parallelism
    if task_count is not None:
        body["overrides"]["taskCount"] = task_count
    if container_overrides:
        body["overrides"]["containerOverrides"] = container_overrides
    encoded = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=encoded,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return json.loads(response.read().decode("utf-8"))
