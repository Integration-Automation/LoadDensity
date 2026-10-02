"""
Azure Container Instances (ACI) ephemeral worker adapter.

Launches one-shot containers via the Azure REST API. Uses
``azure-identity`` + ``azure-mgmt-containerinstance`` (both lazy).
"""

import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ._validation import (
    CloudLaunchError,
    positive_integer,
    positive_number,
    required_string,
    sdk_error_types,
    validate_environment,
)


def _import_azure():
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.containerinstance import ContainerInstanceManagementClient
        from azure.mgmt.containerinstance.models import (
            Container,
            ContainerGroup,
            ContainerGroupRestartPolicy,
            EnvironmentVariable,
            OperatingSystemTypes,
            ResourceRequests,
            ResourceRequirements,
        )
    except ImportError as error:
        raise RuntimeError(
            "azure-identity + azure-mgmt-containerinstance are required for "
            "the Azure ACI adapter; install with: pip install azure-identity "
            "azure-mgmt-containerinstance"
        ) from error
    return {
        "DefaultAzureCredential": DefaultAzureCredential,
        "Client": ContainerInstanceManagementClient,
        "Container": Container,
        "ContainerGroup": ContainerGroup,
        "RestartPolicy": ContainerGroupRestartPolicy,
        "EnvironmentVariable": EnvironmentVariable,
        "OSType": OperatingSystemTypes,
        "ResourceRequests": ResourceRequests,
        "ResourceRequirements": ResourceRequirements,
    }


def launch_aci_workers(
    subscription_id: str,
    resource_group: str,
    location: str,
    image: str,
    workers: int,
    cpu: float = 1.0,
    memory_gb: float = 1.5,
    overrides_env: Optional[Dict[str, str]] = None,
    name_prefix: str = "loaddensity-worker",
) -> List[Dict[str, Any]]:
    """Provision positive ``workers`` groups with unique names per launch.

    Wait for each SDK poller to complete and return name/status/resource_id.
    CloudLaunchError preserves earlier provisioned responses on partial failure.
    No create request is retried and existing groups are never rolled back.
    """
    positive_integer(workers, "workers")
    positive_number(cpu, "cpu")
    positive_number(memory_gb, "memory_gb")
    for value, name in [(subscription_id, "subscription_id"), (resource_group, "resource_group"),
                        (location, "location"), (image, "image")]:
        required_string(value, name)
    _validate_prefix(name_prefix, workers)
    validate_environment(overrides_env)
    _validate_environment_names(overrides_env)
    az = _import_azure()
    service_errors = sdk_error_types("azure")
    try:
        credential = az["DefaultAzureCredential"]()
        client = az["Client"](credential, subscription_id)
    except service_errors as error:
        raise CloudLaunchError("aci", list(range(workers)), [], "client initialization failed") from error

    base_env = [
        az["EnvironmentVariable"](name=k, value=v)
        for k, v in (overrides_env or {}).items()
    ]
    requirements = az["ResourceRequirements"](
        requests=az["ResourceRequests"](memory_in_gb=memory_gb, cpu=cpu),
    )

    responses: List[Dict[str, Any]] = []
    invocation_id = uuid4().hex[:12]
    for index in range(workers):
        name = f"{name_prefix}-{invocation_id}-{index}"
        env = base_env + [
            az["EnvironmentVariable"](name="LD_WORKER_INDEX", value=str(index)),
            az["EnvironmentVariable"](name="LD_WORKER_COUNT", value=str(workers)),
        ]
        container = az["Container"](
            name=name,
            image=image,
            resources=requirements,
            environment_variables=env,
        )
        group = az["ContainerGroup"](
            location=location,
            containers=[container],
            os_type=az["OSType"].linux,
            restart_policy=az["RestartPolicy"].never,
        )
        try:
            poller = client.container_groups.begin_create_or_update(
                resource_group_name=resource_group, container_group_name=name, container_group=group)
            if not callable(getattr(poller, "result", None)):
                raise CloudLaunchError("aci", [index], responses, "malformed provisioning poller", {"name": name})
            result = poller.result()
        except service_errors as error:
            raise CloudLaunchError("aci", [index], responses, "provisioning failed",
                                   {"name": name}) from error
        responses.append(_judge_provisioning(result, name, index, responses))
    return responses


def _validate_prefix(name_prefix: str, workers: int) -> None:
    required_string(name_prefix, "name_prefix")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", name_prefix):
        raise ValueError("name_prefix must contain lowercase letters, digits and internal hyphens")
    if len(name_prefix) + 14 + len(str(workers - 1)) > 63:
        raise ValueError("name_prefix is invalid or too long for unique worker names")


def _validate_environment_names(environment: Optional[Dict[str, str]]) -> None:
    for name in environment or {}:
        if len(name) > 63 or not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9_]*[a-zA-Z0-9])?", name):
            raise ValueError("ACI environment names require 1 to 63 alphanumeric/internal underscore characters")


def _judge_provisioning(result: Any, name: str, index: int,
                        responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    resource_id = getattr(result, "id", None)
    state = getattr(result, "provisioning_state", None)
    if not isinstance(resource_id, str) or not resource_id or state != "Succeeded":
        raise CloudLaunchError("aci", [index], responses, "provisioning failed or malformed",
                               {"name": name, "status": state, "resource_id": resource_id})
    return {"name": name, "status": state, "resource_id": resource_id}
