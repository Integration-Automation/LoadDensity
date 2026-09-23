"""
Azure Container Instances (ACI) ephemeral worker adapter.

Launches one-shot containers via the Azure REST API. Uses
``azure-identity`` + ``azure-mgmt-containerinstance`` (both lazy).
"""

from typing import Any, Dict, List, Optional


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
    """Create ``workers`` ACI container groups. Returns the create responses."""
    az = _import_azure()
    credential = az["DefaultAzureCredential"]()
    client = az["Client"](credential, subscription_id)

    base_env = [
        az["EnvironmentVariable"](name=k, value=v)
        for k, v in (overrides_env or {}).items()
    ]
    requirements = az["ResourceRequirements"](
        requests=az["ResourceRequests"](memory_in_gb=memory_gb, cpu=cpu),
    )

    responses: List[Dict[str, Any]] = []
    for index in range(workers):
        env = base_env + [
            az["EnvironmentVariable"](name="LD_WORKER_INDEX", value=str(index)),
            az["EnvironmentVariable"](name="LD_WORKER_COUNT", value=str(workers)),
        ]
        container = az["Container"](
            name=f"{name_prefix}-{index}",
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
        poller = client.container_groups.begin_create_or_update(
            resource_group_name=resource_group,
            container_group_name=f"{name_prefix}-{index}",
            container_group=group,
        )
        responses.append({"name": f"{name_prefix}-{index}", "status": "submitted",
                          "poller_id": id(poller)})
    return responses
