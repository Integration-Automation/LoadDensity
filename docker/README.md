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

## Installed wheel CI checks

The extras matrix is generated from `pyproject.toml`. Each Docker cell installs the
checkout wheel, runs `pip check`, checks its declared capability without skipping,
and runs the six base smoke tests. GUI cells install Qt system libraries and use
`QT_QPA_PLATFORM=offscreen`. These installation probes use local codecs, stubbed
SDK calls and client configuration; live protocol checks run separately.

```bash
python -m build --wheel --no-isolation
docker build -f docker/extras.Dockerfile --build-arg EXTRA=etcd -t ld-check .
docker run --rm ld-check
```

Use `--build-arg PYTHON_VERSION=3.14` to select a supported Python minor. The
`etcd` extra uses `etcd3gw`, so the target etcd server must enable its v3 HTTP gateway.
Legacy manually installed `etcd3` remains a fallback when `etcd3gw` is unavailable.

The dedicated Compose job has no exposed host ports or fixed container names. It
waits for healthy Redis/MQTT services, checks actual adapter operations and MQTT
delivery, and verifies a SQLite query. Use a unique project name for local runs:

```bash
docker compose -p ld-check -f docker/ci-services.yml build probe
docker compose -p ld-check -f docker/ci-services.yml up -d --wait --wait-timeout 60 redis mosquitto
docker compose -p ld-check -f docker/ci-services.yml run --rm probe
docker compose -p ld-check -f docker/ci-services.yml down --volumes --remove-orphans
```

CI always cleans up this project, including on failure. Publishing depends on the
reusable extras workflow. Pull requests test every extra on Python 3.12 and base on
3.10/3.14; scheduled runs test every cell on 3.10–3.14.
