# LoadDensity local lab

A docker-compose file that brings up every target the examples need:

| Service | Port | Purpose |
|---|---|---|
| `httpbin` | `:8080` | Generic HTTP echo server. |
| `mosquitto` | `:1883` | MQTT broker for `examples/mqtt_pubsub.py`. |
| `redis` | `:6379` | Redis for `examples/redis_load.json`. |
| `kafka` | `:9092` | Single-broker Kafka cluster (KRaft mode). |
| `prometheus` | `:9090` | Scrapes the LoadDensity Prometheus exporter on the host. |

## Quick start

```bash
docker compose -f docker/docker-compose.yml up -d
# … run examples …
docker compose -f docker/docker-compose.yml down -v
```

## Notes

* The Prometheus job scrapes `host.docker.internal:9646`, which is the
  default port of `start_prometheus_exporter`. On Linux without
  `host.docker.internal`, point the job at your host IP instead.
* Kafka uses KRaft (no Zookeeper) and exposes a single broker — good
  enough for examples, not for production load.
* `mosquitto.conf` allows anonymous connections; tighten before
  exposing the broker.
