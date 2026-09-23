"""
AWS Fargate ephemeral worker adapter.

Launches a one-shot ECS task on Fargate that runs the LoadDensity image
in worker mode. The caller pre-provisions an ECS cluster + task
definition; this helper just submits ``run_task`` calls in bulk.
"""

from typing import Any, Dict, List, Optional


def _import_boto3():
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError(
            "boto3 is required for the AWS Fargate adapter; "
            "install with: pip install boto3"
        ) from error
    return boto3


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
    """Launch ``workers`` ECS tasks on Fargate. Returns the run_task responses."""
    boto3 = _import_boto3()
    client = boto3.client("ecs", region_name=region_name)
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
        responses.append(response)
    return responses
