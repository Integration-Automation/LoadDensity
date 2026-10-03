"""
Chart-rendering reports backed by matplotlib (soft-dep).

Two charts are produced from ``test_record_instance``:

* Latency over time (p50 line, p50–p95 and p95–p99 bands)
* Rolling RPS (line, 1-second buckets)

matplotlib is imported lazily. Install with ``pip install matplotlib``
or via the ``[charts]`` extra.
"""

import os
from itertools import chain
from typing import Dict

from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.utils.test_record.window_statistics import latency_windows


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


def _render_latency_chart(plt, output_path: str, windows) -> str:
    fig, ax = plt.subplots(figsize=(10, 4))
    xs = [item["start_time"] for item in windows]
    bands = {key: [item[key] if item[key] is not None else float("nan") for item in windows]
             for key in ("p50_ms", "p95_ms", "p99_ms")}
    ax.fill_between(xs, bands["p50_ms"], bands["p95_ms"], alpha=0.35, label="p50–p95")
    ax.fill_between(xs, bands["p95_ms"], bands["p99_ms"], alpha=0.2, label="p95–p99")
    ax.plot(xs, bands["p50_ms"], marker=".", label="p50")
    ax.set_xlabel("Request start (epoch seconds)")
    ax.set_ylabel("Response time (ms)")
    ax.set_title("LoadDensity latency over time")
    ax.grid(True, alpha=0.3)
    ax.legend()
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
    max_buckets: int = 10000,
) -> Dict[str, str]:
    """
    Render latency + RPS charts. Writes
    ``<report_name>-latency.png`` and ``<report_name>-rps.png`` and
    returns ``{"latency": path, "rps": path}``.
    """
    plt = _require_matplotlib()
    records = chain(test_record_instance.test_record_list, test_record_instance.error_record_list)
    windows = latency_windows(records, bucket_size_seconds=bucket_size_seconds, max_buckets=max_buckets)
    if not any(item["p50_ms"] is not None for item in windows):
        raise ChartDependencyError("no records to render charts")

    latency_path = _render_latency_chart(plt, f"{report_name}-latency.png",
                                          windows)
    rps_xs = [item["start_time"] for item in windows]
    rps_counts = [item["rps"] for item in windows]
    rps_path = _render_rps_chart(plt, f"{report_name}-rps.png", rps_xs, rps_counts)
    return {"latency": latency_path, "rps": rps_path}
