"""Non-skipping installation probes for every declared package extra."""

import argparse
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

import platform_probes
import protocol_probes

PROBES: dict[str, Callable[[], None]] = {
    "amqp": protocol_probes.amqp, "auth": platform_probes.auth,
    "aws": platform_probes.aws, "azure": platform_probes.azure,
    "cassandra": protocol_probes.cassandra, "charts": platform_probes.charts,
    "cloud": platform_probes.cloud, "coap": protocol_probes.coap,
    "couchbase": protocol_probes.couchbase, "datadog": platform_probes.datadog,
    "elasticsearch": protocol_probes.elasticsearch, "etcd": protocol_probes.etcd,
    "faker": platform_probes.faker, "gcp": platform_probes.gcp,
    "grpc": protocol_probes.grpc, "gui": platform_probes.gui,
    "http2": protocol_probes.http2, "http3": protocol_probes.http3,
    "k8s": platform_probes.k8s, "kafka": protocol_probes.kafka,
    "ldap": protocol_probes.ldap, "mcp": platform_probes.mcp,
    "memcached": protocol_probes.memcached, "metrics": platform_probes.metrics,
    "modbus": protocol_probes.modbus, "mongo": protocol_probes.mongo,
    "mqtt": protocol_probes.mqtt, "nats": protocol_probes.nats,
    "neo4j": protocol_probes.neo4j, "opcua": protocol_probes.opcua,
    "opentelemetry": platform_probes.opentelemetry, "pdf": platform_probes.pdf,
    "prometheus": platform_probes.prometheus, "pulsar": protocol_probes.pulsar,
    "redis": protocol_probes.redis, "reliability": platform_probes.reliability,
    "sftp": protocol_probes.sftp, "snmp": protocol_probes.snmp,
    "sql": protocol_probes.sql, "thrift": protocol_probes.thrift,
    "webpush": protocol_probes.webpush, "websocket": protocol_probes.websocket,
    "yaml": platform_probes.yaml, "zmq": protocol_probes.zmq,
}


def run_probe(extra: str) -> None:
    """Fail if a declared dependency/capability is unavailable; never turn failures into skips."""
    if extra == "base":
        return  # All cells run the full installed-wheel base smoke harness separately.
    selected = list(PROBES) if extra == "all" else [extra]
    failed = []
    for name in selected:
        if name not in PROBES:
            raise ValueError(f"extra: missing capability probe for {name}")
        try:
            if extra == "all":
                # Each capability chooses its scheduler before SDK/TLS imports.
                subprocess.run([sys.executable, str(Path(__file__).resolve()), name], check=True, timeout=120)
            else:
                PROBES[name]()
            print(f"capability passed: {name}", flush=True)
        except Exception:
            if extra != "all":
                raise
            traceback.print_exc()
            failed.append(name)
    if failed:
        raise RuntimeError(f"Failed extra capabilities: {', '.join(failed)}")


if __name__ == "__main__":
    import je_load_density  # noqa: F401 - exercise capabilities under the installed framework's runtime.

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extra")
    run_probe(parser.parse_args().extra)
