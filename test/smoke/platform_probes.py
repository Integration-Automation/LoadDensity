"""Cloud SDK, telemetry and rendering capabilities with no provisioned external resources."""

import io
import json
import os
import tempfile
from pathlib import Path


def auth() -> None:
    from cryptography.fernet import Fernet

    cipher = Fernet(Fernet.generate_key())
    if cipher.decrypt(cipher.encrypt(b"smoke")) != b"smoke":
        raise RuntimeError("Cryptographic round-trip failed")


def aws() -> None:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    from botocore.stub import Stubber

    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
    client = boto3.client("ecs", region_name="us-east-1", config=Config(signature_version=UNSIGNED))
    try:
        with Stubber(client) as stub:
            stub.add_response("describe_clusters", {"clusters": [], "failures": []}, {"clusters": ["smoke"]})
            if client.describe_clusters(clusters=["smoke"])["failures"]:
                raise RuntimeError("AWS modeled request failed")
    finally:
        client.close()


def azure() -> None:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.containerinstance.models import Container, ResourceRequests, ResourceRequirements

    credential = DefaultAzureCredential()
    try:
        container = Container(name="smoke", image="python:3.12-slim",
                              resources=ResourceRequirements(requests=ResourceRequests(cpu=1, memory_in_gb=1)))
        if container.as_dict()["resources"]["requests"]["cpu"] != 1:
            raise RuntimeError("Azure container configuration failed")
    finally:
        credential.close()


def gcp() -> None:
    from google.auth.credentials import AnonymousCredentials
    from google.auth.transport.requests import AuthorizedSession

    with AuthorizedSession(AnonymousCredentials()) as session:
        if not session.credentials.valid:
            raise RuntimeError("Google authorized-session configuration failed")


def cloud() -> None:
    aws()
    azure()
    gcp()


def charts() -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot

    figure, axes = pyplot.subplots()
    try:
        axes.plot([0, 1], [10, 20])
        axes.fill_between([0, 1], [10, 20], [30, 40])
        output = io.BytesIO()
        figure.savefig(output, format="png")
        if not output.getvalue().startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("Chart rendering failed")
    finally:
        pyplot.close(figure)


def datadog() -> None:
    os.environ["DD_TRACE_ENABLED"] = "false"
    os.environ["DD_INSTRUMENTATION_TELEMETRY_ENABLED"] = "false"
    from ddtrace.trace import tracer

    with tracer.trace("loaddensity.smoke") as span:
        span.set_tag("smoke", True)
    tracer.shutdown()


def faker() -> None:
    from faker import Faker

    if not Faker().name():
        raise RuntimeError("Fake-data generation failed")


def gui() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication

    from je_load_density.gui.main_window import LoadDensityUI

    application = QApplication.instance() or QApplication([])
    window = LoadDensityUI()
    try:
        window.show()
        application.processEvents()
        if not window.isVisible():
            raise RuntimeError("GUI offscreen launch failed")
    finally:
        window.close()
        application.processEvents()


def k8s() -> None:
    import kopf
    from kubernetes import client

    pod = client.V1Pod(metadata=client.V1ObjectMeta(name="smoke"))
    with client.ApiClient() as api:
        if api.sanitize_for_serialization(pod)["metadata"]["name"] != "smoke":
            raise RuntimeError("Kubernetes model serialization failed")
    if not callable(kopf.on.create):
        raise RuntimeError("Kubernetes operator registration unavailable")


def prometheus() -> None:
    from prometheus_client import CollectorRegistry, Counter, generate_latest

    registry = CollectorRegistry()
    counter = Counter("loaddensity_smoke", "Smoke requests", registry=registry)
    counter.inc()
    if b"loaddensity_smoke_total 1.0" not in generate_latest(registry):
        raise RuntimeError("Prometheus collection failed")


def opentelemetry() -> None:
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader

    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    exporter = OTLPMetricExporter(endpoint="http://127.0.0.1:9", insecure=True)
    try:
        provider.get_meter("smoke").create_counter("requests").add(1)
        data = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics[0].data
        if data.data_points[0].value != 1:
            raise RuntimeError("OpenTelemetry metric collection failed")
    finally:
        exporter.shutdown()
        provider.shutdown()


def metrics() -> None:
    prometheus()
    opentelemetry()


def pdf() -> None:
    from reportlab.pdfgen.canvas import Canvas

    output = io.BytesIO()
    canvas = Canvas(output)
    canvas.drawString(10, 10, "LoadDensity smoke")
    canvas.save()
    if not output.getvalue().startswith(b"%PDF-"):
        raise RuntimeError("PDF rendering failed")


def reliability() -> None:
    import psutil

    if psutil.Process().memory_info().rss <= 0:
        raise RuntimeError("Process resource inspection failed")


def yaml() -> None:
    import yaml as yaml_sdk

    expected = {"load_density": [["print", ["smoke"]]]}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "actions.yaml"
        path.write_text(yaml_sdk.safe_dump(expected), encoding="utf-8")
        if yaml_sdk.safe_load(path.read_text(encoding="utf-8")) != expected:
            raise RuntimeError("YAML action round-trip failed")


def mcp() -> None:
    import subprocess
    import sys

    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                          "clientInfo": {"name": "extras-probe", "version": "1"}}}
    response = subprocess.run([sys.executable, "-m", "je_load_density.mcp_server"],
                              input=json.dumps(request) + "\n", text=True, capture_output=True,
                              timeout=30, check=True)
    if "protocolVersion" not in json.loads(response.stdout.splitlines()[0])["result"]:
        raise RuntimeError("MCP handshake failed")
