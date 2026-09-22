"""
Latency histogram report (matplotlib lazy import).

Renders a histogram + log-scale CDF of latency in milliseconds.
"""

import os
from typing import Dict, List

from je_load_density.utils.test_record.test_record_class import test_record_instance


class HistogramDependencyError(RuntimeError):
    """Raised when matplotlib is not installed."""


def _require_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise HistogramDependencyError(
            "matplotlib is required for histogram reports. "
            "Install with: pip install matplotlib"
        ) from error
    return plt


def _collect_latencies() -> List[float]:
    return [
        float(record["response_time_ms"])
        for record in test_record_instance.test_record_list
        if record.get("response_time_ms") is not None
    ]


def _render_histogram(plt, output_path: str, latencies: List[float], bins: int) -> str:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(latencies, bins=bins, alpha=0.7, edgecolor="black")
    ax.set_xlabel("Response time (ms)")
    ax.set_ylabel("Frequency")
    ax.set_title("LoadDensity latency histogram")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return os.path.abspath(output_path)


def _render_cdf(plt, output_path: str, latencies: List[float]) -> str:
    ordered = sorted(latencies)
    ys = [(i + 1) / len(ordered) for i in range(len(ordered))]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(ordered, ys)
    ax.set_xscale("log")
    ax.set_xlabel("Response time (ms, log)")
    ax.set_ylabel("Cumulative fraction")
    ax.set_title("LoadDensity latency CDF")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return os.path.abspath(output_path)


def generate_histogram_report(
    report_name: str = "loaddensity-histogram",
    bins: int = 50,
) -> Dict[str, str]:
    """Render latency histogram + CDF, return ``{"histogram": p, "cdf": p}``."""
    plt = _require_matplotlib()
    latencies = _collect_latencies()
    if not latencies:
        raise HistogramDependencyError("no records to render histogram")
    histogram_path = _render_histogram(
        plt, f"{report_name}-histogram.png", latencies, bins,
    )
    cdf_path = _render_cdf(plt, f"{report_name}-cdf.png", latencies)
    return {"histogram": histogram_path, "cdf": cdf_path}
