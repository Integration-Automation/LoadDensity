"""
Chart-rendering reports backed by matplotlib (soft-dep).

Two charts are produced from ``test_record_instance``:

* Latency over time (scatter, per request)
* Rolling RPS (line, 1-second buckets)

matplotlib is imported lazily. Install with ``pip install matplotlib``
or via the ``[charts]`` extra.
"""

import os
from typing import Dict, List, Tuple

from je_load_density.utils.test_record.test_record_class import test_record_instance


class ChartDependencyError(RuntimeError):
    """Raised when matplotlib is not installed."""


def _require_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise ChartDependencyError(
            "matplotlib is required for chart reports. "
            "Install with: pip install matplotlib"
        ) from error
    return plt


def _collect_points() -> Tuple[List[float], List[float]]:
    timestamps: List[float] = []
    latencies: List[float] = []
    for index, record in enumerate(test_record_instance.test_record_list):
        latency = record.get("response_time_ms")
        if latency is None:
            continue
        timestamps.append(float(record.get("ts") or index))
        latencies.append(float(latency))
    return timestamps, latencies


def _bucket_rps(timestamps: List[float], bucket_size: float = 1.0) -> Tuple[List[float], List[int]]:
    if not timestamps:
        return [], []
    start = min(timestamps)
    buckets: Dict[int, int] = {}
    for ts in timestamps:
        idx = int((ts - start) // bucket_size)
        buckets[idx] = buckets.get(idx, 0) + 1
    xs = sorted(buckets.keys())
    return [start + x * bucket_size for x in xs], [buckets[x] for x in xs]


def _render_latency_chart(plt, output_path: str, timestamps, latencies) -> str:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.scatter(timestamps, latencies, s=8, alpha=0.6)
    ax.set_xlabel("Request index (or timestamp)")
    ax.set_ylabel("Response time (ms)")
    ax.set_title("LoadDensity latency over time")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return os.path.abspath(output_path)


def _render_rps_chart(plt, output_path: str, xs, counts) -> str:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xs, counts, marker="o", markersize=4)
    ax.set_xlabel("Time bucket")
    ax.set_ylabel("Requests per second")
    ax.set_title("LoadDensity RPS over time")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return os.path.abspath(output_path)


def generate_chart_report(
    report_name: str = "loaddensity-charts",
    bucket_size_seconds: float = 1.0,
) -> Dict[str, str]:
    """
    Render latency + RPS charts. Writes
    ``<report_name>-latency.png`` and ``<report_name>-rps.png`` and
    returns ``{"latency": path, "rps": path}``.
    """
    plt = _require_matplotlib()
    timestamps, latencies = _collect_points()
    if not latencies:
        raise ChartDependencyError("no records to render charts")

    latency_path = _render_latency_chart(plt, f"{report_name}-latency.png",
                                          timestamps, latencies)
    rps_xs, rps_counts = _bucket_rps(timestamps, bucket_size_seconds)
    rps_path = _render_rps_chart(plt, f"{report_name}-rps.png", rps_xs, rps_counts)
    return {"latency": latency_path, "rps": rps_path}
