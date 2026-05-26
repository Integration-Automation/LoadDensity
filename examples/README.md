# LoadDensity Examples

Runnable recipes that exercise the framework end-to-end. Each example is
self-contained; uncomment / adjust hostnames to point at your own stack
or the docker-compose lab under [`../docker/`](../docker/).

Run a Python example directly:

```bash
python examples/auth_flow.py
```

Run an action JSON example through the CLI:

```bash
python -m je_load_density run examples/quick_smoke.json
```

| Example | Demonstrates |
|---|---|
| [`quick_smoke.json`](quick_smoke.json) | Minimal `LD_start_test` → `LD_generate_summary_report` over httpbin. |
| [`auth_flow.py`](auth_flow.py) | Login extract → reuse `${var.auth}` Bearer header on protected calls. |
| [`weighted_mix.json`](weighted_mix.json) | `mode: "weighted"` traffic shaping with per-task weights. |
| [`sla_gates.json`](sla_gates.json) | Summary report + `LD_assert_sla` p95 / failure-rate gates. |
| [`har_replay.py`](har_replay.py) | HAR → action JSON → execute. |
| [`graphql_query.py`](graphql_query.py) | GraphQL helper composed into an HTTP user template. |
| [`websocket_echo.py`](websocket_echo.py) | WebSocket connect → sendrecv → close with `expect`. |
| [`mqtt_pubsub.py`](mqtt_pubsub.py) | MQTT pub/sub against a local Mosquitto broker. |
| [`redis_load.json`](redis_load.json) | Redis GET / SET / INCR loop. |
| [`spike_shape.json`](spike_shape.json) | `LoadTestShape` integration with the spike profile. |
| [`postman_to_action.py`](postman_to_action.py) | Postman collection → action JSON in two lines. |
| [`openapi_to_action.py`](openapi_to_action.py) | OpenAPI spec → action JSON with `${var.id}` path placeholders. |
