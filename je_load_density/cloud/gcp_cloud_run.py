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

from ._validation import CloudLaunchError, positive_integer, positive_number, required_string


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
    if not isinstance(credentials.token, str) or not credentials.token.strip():
        raise RuntimeError("Cloud Run credential refresh returned an empty token")
    return credentials.token


def _validate_overrides(container_overrides: Optional[List[Dict[str, Any]]]) -> None:
    if container_overrides is None:
        return
    if not isinstance(container_overrides, list):
        raise ValueError("container_overrides must be a list")
    for override in container_overrides:
        if not isinstance(override, dict) or not override:
            raise ValueError("each container override must be a nonempty object")
        if set(override) - {"name", "args", "env", "clearArgs"}:
            raise ValueError("unsupported container override field")
        _validate_container_override(override)


def _validate_container_override(override: Dict[str, Any]) -> None:
    if "name" in override:
        required_string(override["name"], "container name")
    if "clearArgs" in override and not isinstance(override["clearArgs"], bool):
        raise ValueError("clearArgs must be a boolean")
    if "args" in override:
        args = override["args"]
        if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
            raise ValueError("container args must be a list of strings")
    if "env" in override:
        _validate_env(override["env"])


def _validate_env(environment: List[Dict[str, str]]) -> None:
    if not isinstance(environment, list):
        raise ValueError("container env must be a list")
    for variable in environment:
        if not isinstance(variable, dict) or set(variable) - {"name", "value", "valueSource"}:
            raise ValueError("invalid container environment variable")
        required_string(variable.get("name"), "environment name")
        if "value" in variable and not isinstance(variable["value"], str):
            raise ValueError("environment value must be a string")
        if "valueSource" in variable:
            if "value" in variable:
                raise ValueError("environment value and valueSource are mutually exclusive")
            _validate_value_source(variable["valueSource"])


def _validate_value_source(source: Dict[str, Any]) -> None:
    if not isinstance(source, dict) or set(source) != {"secretKeyRef"}:
        raise ValueError("valueSource must contain secretKeyRef")
    secret = source["secretKeyRef"]
    if not isinstance(secret, dict) or set(secret) - {"secret", "version"}:
        raise ValueError("secretKeyRef must be an object with secret and optional version")
    required_string(secret.get("secret"), "secret name")
    if "version" in secret:
        required_string(secret["version"], "secret version")


def _judge_operation(body: bytes) -> Dict[str, Any]:
    try:
        response = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CloudLaunchError("cloud_run", [0], [], "malformed operation JSON") from error
    if not isinstance(response, dict) or not isinstance(response.get("name"), str):
        raise CloudLaunchError("cloud_run", [0], [], "malformed operation")
    if not response["name"].strip() or "error" in response:
        raise CloudLaunchError("cloud_run", [0], [], "operation failed or malformed", response)
    return response


def run_cloud_run_job(
    project: str,
    region: str,
    job_name: str,
    parallelism: Optional[int] = None,
    task_count: Optional[int] = None,
    container_overrides: Optional[List[Dict[str, Any]]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Trigger a Job and return its Operation; submission does not imply completion.

    jobs.run supports task_count and container overrides. Set parallelism on the
    deployed Job; specifying it here raises ValueError before authentication.
    Credentials refresh each call. HTTP/authentication errors propagate and no
    potentially accepted POST is retried.
    """
    for value, name in [(project, "project"), (region, "region"), (job_name, "job_name")]:
        required_string(value, name)
    if parallelism is not None:
        raise ValueError("parallelism is not a jobs.run override; configure it on the deployed Job")
    if task_count is not None:
        positive_integer(task_count, "task_count")
    positive_number(timeout, "timeout")
    _validate_overrides(container_overrides)
    token = _bearer_token(["https://www.googleapis.com/auth/cloud-platform"])
    # Each name is one path segment; quoting keeps a stray "/" or "?" from addressing another resource.
    project, region, job_name = (urllib.parse.quote(str(part), safe="") for part in (project, region, job_name))
    url = (
        f"https://run.googleapis.com/v2/projects/{project}/locations/"
        f"{region}/jobs/{job_name}:run"
    )
    body: Dict[str, Any] = {"overrides": {}}
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
        return _judge_operation(response.read())
