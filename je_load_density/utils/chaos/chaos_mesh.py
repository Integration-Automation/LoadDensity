"""
Chaos Mesh launcher — applies CRD manifests via ``kubectl``.

Stdlib only; the user must have ``kubectl`` on PATH. The helper just
writes the manifest to a temp file and invokes kubectl apply / delete.
"""

import json as json_module
import shutil
import subprocess  # nosec - kubectl invocation is intentional
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def _require_kubectl() -> str:
    binary = shutil.which("kubectl")
    if binary is None:
        raise RuntimeError("kubectl not found on PATH")
    return binary


def _run(binary: str, args: List[str], timeout: float) -> str:
    completed = subprocess.run(  # nosec - args are a constructed list, no shell
        [binary, *args],
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace"))
    return completed.stdout.decode("utf-8", errors="replace")


def _kubectl_with_manifest(
    verb_args: List[str],
    manifest: Dict[str, Any],
    namespace: Optional[str],
    timeout: float,
) -> str:
    """Write ``manifest`` to a temporary JSON file, run ``kubectl <verb_args> -f <file>``, delete the file."""
    binary = _require_kubectl()
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".json", delete=False,
    ) as handle:
        json_module.dump(manifest, handle)
        manifest_path = handle.name

    try:
        args = [verb_args[0], "-f", manifest_path, *verb_args[1:]]
        if namespace:
            args.extend(["-n", namespace])
        return _run(binary, args, timeout)
    finally:
        Path(manifest_path).unlink(missing_ok=True)


def apply_manifest(
    manifest: Dict[str, Any],
    namespace: Optional[str] = None,
    timeout: float = 30.0,
) -> str:
    """Apply a Chaos Mesh manifest dict via ``kubectl apply``."""
    return _kubectl_with_manifest(["apply"], manifest, namespace, timeout)


def delete_manifest(
    manifest: Dict[str, Any],
    namespace: Optional[str] = None,
    timeout: float = 30.0,
) -> str:
    """Delete a Chaos Mesh manifest dict via ``kubectl delete``."""
    return _kubectl_with_manifest(["delete", "--ignore-not-found"], manifest, namespace, timeout)


def build_network_delay(
    name: str,
    namespace: str,
    selector_labels: Dict[str, str],
    latency: str = "100ms",
    duration: str = "30s",
) -> Dict[str, Any]:
    """Construct a NetworkChaos delay manifest."""
    return {
        "apiVersion": "chaos-mesh.org/v1alpha1",
        "kind": "NetworkChaos",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "action": "delay",
            "mode": "all",
            "selector": {"labelSelectors": selector_labels},
            "delay": {"latency": latency},
            "duration": duration,
        },
    }
