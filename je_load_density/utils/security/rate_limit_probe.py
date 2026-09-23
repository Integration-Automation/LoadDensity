"""
Rate-limit probe.

Issues bursts of an HTTP request and returns the request count at
which the server begins returning rate-limit responses (HTTP 429 or
custom). Uses stdlib urllib so there's no extra dep.
"""

import time
import urllib.request
from typing import Any, Dict, Optional

from je_load_density.utils.logging.loggin_instance import load_density_logger


def probe_rate_limit(
    url: str,
    method: str = "GET",
    burst: int = 100,
    delay_ms: int = 0,
    timeout: float = 2.0,
    headers: Optional[Dict[str, str]] = None,
    rate_limit_statuses: Optional[set] = None,
) -> Dict[str, Any]:
    """
    Send up to ``burst`` requests until a rate-limit response is seen.

    Returns a dict with the index of the first throttled request, the
    total response time, and the first throttle header observed (if any).
    """
    headers = headers or {}
    rate_limit_statuses = rate_limit_statuses or {429, 503}
    first_throttle: Optional[int] = None
    first_headers: Dict[str, str] = {}
    start = time.monotonic()
    for index in range(burst):
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
                status = response.status
                response_headers = {k: v for k, v in response.getheaders()}
        except urllib.request.HTTPError as error:
            status = error.code
            response_headers = {k: v for k, v in (error.headers.items() if error.headers else [])}
        except Exception as error:  # noqa: BLE001 - an unreachable request is not a throttle
            load_density_logger.debug(f"probe_rate_limit: request {index} failed: {error!r}")
            continue  # nosec B112 - logged above
        if status in rate_limit_statuses and first_throttle is None:
            first_throttle = index
            first_headers = response_headers
            break
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
    return {
        "first_throttled_at": first_throttle,
        "elapsed_seconds": time.monotonic() - start,
        "throttle_headers": {
            k: v for k, v in first_headers.items()
            if k.lower().startswith(("x-ratelimit", "retry-after"))
        },
    }
