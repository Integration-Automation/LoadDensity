"""
Toxiproxy HTTP client — inject latency / disconnects between LoadDensity
and the SUT during a test. Uses urllib so no extra dependency is needed.
"""

import json as json_module
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def _require_http_scheme(url: str) -> None:
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported toxiproxy scheme: {scheme!r}")


def _segment(name: str) -> str:
    """Quote a proxy or toxic name for use as one URL path segment.

    A name containing ``/``, ``?`` or ``#`` would otherwise address a different Toxiproxy
    endpoint than the one the caller named.
    """
    return urllib.parse.quote(str(name), safe="")


def _request(method: str, url: str, body: Optional[bytes], timeout: float) -> bytes:
    _require_http_scheme(url)
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return response.read()


def list_proxies(base_url: str = "http://127.0.0.1:8474", timeout: float = 5.0) -> Dict[str, Any]:
    """Return Toxiproxy's proxy registry."""
    data = _request("GET", f"{base_url.rstrip('/')}/proxies", None, timeout)
    return json_module.loads(data.decode("utf-8") or "{}")


def create_proxy(
    name: str,
    listen: str,
    upstream: str,
    enabled: bool = True,
    base_url: str = "http://127.0.0.1:8474",
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """Create or replace a Toxiproxy proxy."""
    payload = {"name": name, "listen": listen, "upstream": upstream, "enabled": enabled}
    body = json_module.dumps(payload).encode("utf-8")
    data = _request("POST", f"{base_url.rstrip('/')}/proxies", body, timeout)
    return json_module.loads(data.decode("utf-8") or "{}")


def add_toxic(
    proxy_name: str,
    toxic_name: str,
    toxic_type: str,
    attributes: Dict[str, Any],
    stream: str = "downstream",
    base_url: str = "http://127.0.0.1:8474",
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """Attach a toxic (latency, bandwidth, slicer, etc.) to a proxy."""
    payload = {
        "name": toxic_name,
        "type": toxic_type,
        "stream": stream,
        "attributes": attributes,
    }
    body = json_module.dumps(payload).encode("utf-8")
    data = _request(
        "POST", f"{base_url.rstrip('/')}/proxies/{_segment(proxy_name)}/toxics", body, timeout,
    )
    return json_module.loads(data.decode("utf-8") or "{}")


def remove_toxic(
    proxy_name: str,
    toxic_name: str,
    base_url: str = "http://127.0.0.1:8474",
    timeout: float = 5.0,
) -> None:
    """Remove a toxic from a proxy."""
    _request(
        "DELETE",
        f"{base_url.rstrip('/')}/proxies/{_segment(proxy_name)}/toxics/{_segment(toxic_name)}",
        None,
        timeout,
    )


def reset_all(base_url: str = "http://127.0.0.1:8474", timeout: float = 5.0) -> None:
    """Reset every proxy + clear every toxic."""
    _request("POST", f"{base_url.rstrip('/')}/reset", b"", timeout)


def install_latency(
    proxy_name: str,
    latency_ms: int,
    jitter_ms: int = 0,
    base_url: str = "http://127.0.0.1:8474",
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """Convenience wrapper for the common latency toxic."""
    return add_toxic(
        proxy_name=proxy_name,
        toxic_name=f"{proxy_name}-latency",
        toxic_type="latency",
        attributes={"latency": int(latency_ms), "jitter": int(jitter_ms)},
        base_url=base_url,
        timeout=timeout,
    )


def install_bandwidth(
    proxy_name: str,
    rate_kbps: int,
    base_url: str = "http://127.0.0.1:8474",
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """Convenience wrapper for the bandwidth toxic."""
    return add_toxic(
        proxy_name=proxy_name,
        toxic_name=f"{proxy_name}-bandwidth",
        toxic_type="bandwidth",
        attributes={"rate": int(rate_kbps)},
        base_url=base_url,
        timeout=timeout,
    )


def remove_proxies(
    names: List[str],
    base_url: str = "http://127.0.0.1:8474",
    timeout: float = 5.0,
) -> None:
    """Delete the named proxies."""
    for name in names:
        _request("DELETE", f"{base_url.rstrip('/')}/proxies/{_segment(name)}", None, timeout)
