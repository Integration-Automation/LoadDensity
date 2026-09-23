"""
LoadDensity Kubernetes operator (kopf, lazy import).

Watches ``LoadTest`` and ``LoadRun`` CRDs and reconciles them into the
master + worker Pod/Job topology. Designed to be packaged as a
container::

    docker build -t loaddensity-operator deploy/k8s-operator
    kubectl apply -f deploy/k8s-operator/crd.yaml
    kubectl apply -f deploy/k8s-operator/deployment.yaml
"""

from typing import Any, Dict

try:
    import kopf  # type: ignore
except ImportError as error:  # pragma: no cover - operator-only path
    raise RuntimeError(
        "kopf is required for the LoadDensity operator; "
        "install with: pip install kopf kubernetes"
    ) from error

try:
    from kubernetes import client, config  # type: ignore
except ImportError as error:  # pragma: no cover
    raise RuntimeError(
        "kubernetes client is required for the LoadDensity operator; "
        "install with: pip install kubernetes"
    ) from error


_DEFAULT_IMAGE = "ghcr.io/integration-automation/loaddensity:latest"


def _ensure_config() -> None:
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()


def _master_pod_manifest(name: str, namespace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    image = spec.get("image", _DEFAULT_IMAGE)
    action_file = spec.get("actionFile", "/etc/loaddensity/action.json")
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"{name}-master",
            "namespace": namespace,
            "labels": {"app": "loaddensity", "role": "master", "loadtest": name},
        },
        "spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "master",
                "image": image,
                "args": ["python", "-m", "je_load_density", "run", action_file],
                "ports": [{"containerPort": 5557}, {"containerPort": 8089}],
            }],
        },
    }


def _worker_job_manifest(
    name: str, namespace: str, spec: Dict[str, Any],
) -> Dict[str, Any]:
    image = spec.get("image", _DEFAULT_IMAGE)
    parallelism = int(spec.get("workers", 1))
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"{name}-workers",
            "namespace": namespace,
            "labels": {"app": "loaddensity", "role": "worker", "loadtest": name},
        },
        "spec": {
            "parallelism": parallelism,
            "completions": parallelism,
            "backoffLimit": 0,
            "template": {
                "metadata": {
                    "labels": {"app": "loaddensity", "role": "worker", "loadtest": name},
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "worker",
                        "image": image,
                        "args": [
                            "python", "-m", "je_load_density", "run-str",
                            "--runner-mode", "worker",
                            "--master-host", f"{name}-master",
                        ],
                    }],
                },
            },
        },
    }


@kopf.on.create("integration.automation", "v1", "loadtests")
def on_create_loadtest(spec, name, namespace, logger, **_kwargs):
    """Provision a master pod + worker job when a LoadTest CR is created."""
    _ensure_config()
    core = client.CoreV1Api()
    batch = client.BatchV1Api()
    namespace = namespace or "default"

    master = _master_pod_manifest(name, namespace, spec)
    worker = _worker_job_manifest(name, namespace, spec)
    try:
        core.create_namespaced_pod(namespace=namespace, body=master)
    except client.exceptions.ApiException as error:
        if error.status != 409:
            raise
    try:
        batch.create_namespaced_job(namespace=namespace, body=worker)
    except client.exceptions.ApiException as error:
        if error.status != 409:
            raise
    logger.info(f"LoadDensity LoadTest {namespace}/{name} provisioned")
    return {"phase": "Running"}


@kopf.on.delete("integration.automation", "v1", "loadtests")
def on_delete_loadtest(name, namespace, logger, **_kwargs):
    """Tear down master + worker resources when the LoadTest CR is deleted."""
    _ensure_config()
    core = client.CoreV1Api()
    batch = client.BatchV1Api()
    namespace = namespace or "default"
    for resource_name, deleter in (
        (f"{name}-master", lambda r: core.delete_namespaced_pod(r, namespace)),
        (
            f"{name}-workers",
            lambda r: batch.delete_namespaced_job(
                r, namespace, propagation_policy="Foreground",
            ),
        ),
    ):
        try:
            deleter(resource_name)
        except client.exceptions.ApiException as error:
            if error.status != 404:
                raise
    logger.info(f"LoadDensity LoadTest {namespace}/{name} deleted")
