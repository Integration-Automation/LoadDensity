"""
AWS Fargate ephemeral worker adapter.

Launches a one-shot ECS task on Fargate that runs the LoadDensity image
in worker mode. The caller pre-provisions an ECS cluster + task
definition; this helper just submits ``run_task`` calls in bulk.
"""

from typing import Any, Dict, List, Optional

from ._validation import CloudLaunchError, positive_integer, required_string, sdk_error_types, validate_environment


def _import_boto3():
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError(
            "boto3 is required for the AWS Fargate adapter; "
            "install with: pip install boto3"
        ) from error
    return boto3


def _validate_network(subnets: List[str], security_groups: Optional[List[str]], assign_public_ip: bool) -> None:
    if not isinstance(subnets, list) or not 1 <= len(subnets) <= 16:
        raise ValueError("subnets must contain 1 to 16 subnet IDs")
    if security_groups is not None:
        if not isinstance(security_groups, list) or len(security_groups) > 5:
            raise ValueError("security_groups must contain at most 5 IDs")
    for subnet in subnets:
        required_string(subnet, "subnet ID")
    for group in security_groups or []:
        required_string(group, "security group ID")
    if not isinstance(assign_public_ip, bool):
        raise ValueError("assign_public_ip must be a boolean")


def _judge_response(response: Dict[str, Any], index: int, responses: List[Dict[str, Any]]) -> None:
    if not isinstance(response, dict):
        raise CloudLaunchError("fargate", [index], responses, "malformed run_task response")
    tasks = response.get("tasks")
    failures = response.get("failures", [])
    valid_tasks = isinstance(tasks, list) and len(tasks) == 1
    if valid_tasks:
        arn = tasks[0].get("taskArn") if isinstance(tasks[0], dict) else None
        valid_tasks = isinstance(arn, str) and bool(arn.strip())
    if failures or not valid_tasks or not isinstance(failures, list):
        accepted = responses + ([response] if valid_tasks else [])
        raise CloudLaunchError("fargate", [index], accepted, "run_task failed or malformed", response)


def launch_fargate_workers(
    cluster: str,
    task_definition: str,
    workers: int,
    subnets: List[str],
    security_groups: Optional[List[str]] = None,
    assign_public_ip: bool = False,
    region_name: Optional[str] = None,
    container_name: str = "loaddensity",
    overrides_env: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Launch positive ``workers`` tasks; raise CloudLaunchError on partial failure.

    Accepted task responses remain on the exception. No launch is retried or
    rolled back; a returned task ARN confirms submission, not worker readiness.
    """
    positive_integer(workers, "workers")
    for value, name in [(cluster, "cluster"), (task_definition, "task_definition"),
                        (container_name, "container_name")]:
        required_string(value, name)
    _validate_network(subnets, security_groups, assign_public_ip)
    validate_environment(overrides_env)
    boto3 = _import_boto3()
    service_errors = sdk_error_types("aws")
    try:
        client = boto3.client("ecs", region_name=region_name)
    except service_errors as error:
        raise CloudLaunchError("fargate", list(range(workers)), [], "client initialization failed") from error
    env = [{"name": k, "value": v} for k, v in (overrides_env or {}).items()]
    network = {
        "awsvpcConfiguration": {
            "subnets": subnets,
            "securityGroups": security_groups or [],
            "assignPublicIp": "ENABLED" if assign_public_ip else "DISABLED",
        },
    }
    responses: List[Dict[str, Any]] = []
    for index in range(workers):
        try:
            response = client.run_task(
                cluster=cluster,
                taskDefinition=task_definition,
                launchType="FARGATE",
                count=1,
                networkConfiguration=network,
                overrides={"containerOverrides": [{
                    "name": container_name,
                    "environment": env + [
                        {"name": "LD_WORKER_INDEX", "value": str(index)},
                        {"name": "LD_WORKER_COUNT", "value": str(workers)},
                    ],
                }]},
            )
        except service_errors as error:
            raise CloudLaunchError("fargate", [index], responses, "run_task failed") from error
        _judge_response(response, index, responses)
        responses.append(response)
    return responses
