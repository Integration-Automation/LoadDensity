# LoadDensity Architecture

> Short overview for people and agents.
> Last verified: 2026-10-03 against the working tree on `feat/testing-platform`.

## 1. Purpose

LoadDensity (`je_load_density`) is a load and stress testing framework built on Locust. It is
published as `je_load_density` (stable, `pyproject.toml`) and `je_load_density_dev` (dev,
`dev.toml`). A test is described as data: a `user_detail_dict` names a user type and holds its task
lists. `start_test` runs that description, either from Python or from JSON action files through the
`LD_*` executor. Locust request events land in a shared test record. Reports, SLA gates and run
persistence all read from that record.

## 2. Layers and directories

| Path | Responsibility |
| --- | --- |
| `je_load_density/__init__.py` | Public facade (`__all__`). It imports `wrapper/event/request_hook.py` for its side effect, which registers the Locust request hook |
| `je_load_density/__main__.py` | CLI: subcommands plus hidden legacy flags. `main()` is also the `loaddensity` script |
| `je_load_density/wrapper/start_wrapper/start_test.py` | `start_test()` and `_USER_REGISTRY`, which maps a user type to its Locust user class and `set_wrapper_*` initialiser |
| `je_load_density/wrapper/create_locust_env/` | `prepare_env` / `create_env`: Locust environment, runner mode (`local`/`master`/`worker`), load shape, web UI |
| `je_load_density/wrapper/proxy/` | `locust_wrapper_proxy` (`LocustUserProxy.user_dict`) holds each user type's configuration, one `user/<type>_user_proxy.py` per type |
| `je_load_density/wrapper/user_template/` | Locust user classes (`HttpUserWrapper`, `FastHttpUserWrapper`, …) and the task engine `request_executor.py` / `scenario_runner.py`. `_protocol_base.py` and `_common.py` are the shared helpers of the protocol templates |
| `je_load_density/wrapper/event/request_hook.py` | Locust request listener that writes into `test_record_instance` |
| `je_load_density/utils/executor/` | `Executor` (je_action_core's `ActionExecutor` with LoadDensity's settings): `event_dict` (`LD_*` commands plus je_action_core's `SAFE_BUILTINS` allowlist), `execute_action`, `execute_files`, `add_command_to_executor` |
| `je_load_density/utils/test_record/` | `test_record_instance` and SQLite run persistence |
| `je_load_density/utils/generate_report/` | HTML, JSON, XML, CSV, JUnit, summary and chart reports. Also Allure, cost, CycloneDX, Excel, histogram, PDF, SARIF and service-map generators |
| `je_load_density/utils/{parameterization,load_shapes,throttle,reliability,sla,regression,schema,linter,graphql,auth}/` | Variables and CSV sources, load shapes, RPS throttle, retry / failure budget / network conditioner, SLA gates (`evaluate_sla`, `assert_sla`), run diff, action JSON schema, action linter, GraphQL tasks, SigV4 / JWT / OAuth2 helpers |
| `je_load_density/utils/{recording,metrics,notifier,ci_annotations,dashboard}/` | HAR/cURL/Postman/OpenAPI/JMeter/k6 importers, Prometheus/OTel/InfluxDB/StatsD sinks, Slack/Teams notifiers, GitHub annotations, live dashboard. Also CDP capture and a mitmproxy addon, OTel tracing and Datadog APM exporters, PagerDuty/Opsgenie/GitLab notifiers, canary analysis |
| `je_load_density/utils/{socket_server,callback,package_manager,project,json,xml,file_process,get_data_structure,logging,exception}/` | TCP control server, callback executor, package loader, project scaffold, I/O and response-data helpers, `load_density_logger`, exceptions |
| `je_load_density/utils/{action_generator,ai,chaos,data,dx,governance,scenario,security,stub_server}/` | Action generation from OpenAPI or cURL, auto-baseline and tuning helpers, Chaos Mesh / Toxiproxy, data factories, REPL and profiler, audit log and catalog, scenario FSM, security probes, stub server |
| `je_load_density/engine/` | Asyncio HTTP engine without Locust (`run_async_load`) and the `bench` CLI |
| `je_load_density/cloud/` | Worker launchers for AWS Fargate and Lambda, Azure ACI and GCP Cloud Run |
| `je_load_density/mcp_server/` | MCP stdio server |
| `je_load_density/action_lsp/` | LSP server for action JSON, standard library only (diagnostics and `LD_*` completion) |
| `je_load_density/tools/lint_files.py` | Pre-commit entry that lints action JSON files |
| `je_load_density/gui/` | Optional PySide6 GUI (`gui` extra). `LoadDensityWidget` shows the form, the live stats panel and a tab bar with the log, the live chart (`chart_panel.py`) and the run history (`run_history_panel.py`) |
| `editors/vscode/` | VS Code extension that starts the LSP; its action schema is committed under `schemas/`. `editors/chrome-extension/` and `editors/jetbrains/` hold the Chrome and JetBrains extensions. `.github/workflows/editors.yml` builds all three |
| `deploy/` | Helm chart, k8s operator, Terraform, Grafana dashboard, CI templates |
| `docker/`, `action.yml`, `.pre-commit-hooks.yaml`, `examples/` | docker-compose test stack, composite GitHub Action, pre-commit hook, sample actions and scripts |
| `load_density_driver/` | Prebuilt driver (script plus Windows and Linux binaries) |
| `scripts/dev_release.py` | Release helper of the dev channel, standard library only: the next version from PyPI and the changed-wheel check. The `publish-dev` job of `.github/workflows/ci-dev.yml` runs it |
| `test/`, `docs/source/` | pytest suite; Sphinx docs (`En/`, `Zh/`, `api/`) |

## 3. Entry points and public interfaces

- **Python facade** (`import je_load_density`): `start_test`, `execute_action`, `execute_files`,
  `add_command_to_executor`, `executor`, `create_env`, `prepare_env`, `locust_wrapper_proxy`,
  `test_record_instance`, `generate_*_report`, `start_load_density_socket_server`, `callback_executor`,
  `create_project_dir`, and the Locust re-exports `task`, `TaskSet`, `SequentialTaskSet`.
- **Action format**: an action is `[name]`, `[name, {kwargs}]` or `[name, [args]]`. A file holds a
  list of actions or `{"load_density": [...]}`.
- **CLI** (`python -m je_load_density` or `loaddensity`):
  - subcommands `run`, `run-dir`, `run-str`, `init` and `serve` (`--host --port --framed --token
    --tls-cert --tls-key`); also `bench` (asyncio HTTP benchmark) and `shell` (REPL);
  - legacy flags, hidden from `--help`: `-e/--execute_file`, `-d/--execute_dir`, `-c/--create_project`
    and `--execute_str`;
  - on Windows, `run-str` and `--execute_str` decode a second time when the first decode yields a
    string. Exit codes: `0` success, `2` no command, `1` uncaught error.
- **MCP**: `loaddensity-mcp` or `python -m je_load_density.mcp_server`. Tool paths are confined to
  `JE_LOAD_DENSITY_MCP_ROOT` (default: the working directory). `LoadDensityMCPServer`
  (`mcp_server/server.py`) speaks JSON-RPC 2.0 over stdio itself, without the `mcp` SDK: importing the package
  imports locust, whose gevent `patch_all()` stalls the SDK's thread-based stdin reader. `run_stdio()` moves
  everything else written to stdout onto stderr. Tools are the `load_density.*` entries in `_TOOLS`.
- **LSP**: `loaddensity-lsp` or `python -m je_load_density.action_lsp` (stdio). `editors/vscode/extension.js`
  starts it with `-m je_load_density.action_lsp`.
- **TCP control server**: `start_load_density_socket_server(host="localhost", port=9940, framed, token, certfile, keyfile)`.
  The token can also come from `LOAD_DENSITY_SOCKET_TOKEN`. Replies end with `Return_Data_Over_JE\n`.
  Starting the server calls gevent `monkey.patch_all()`.
- **CI hooks**: `action.yml` lints, runs `python -m je_load_density run`, then emits annotations.
  `.pre-commit-hooks.yaml` runs `python -m je_load_density.tools.lint_files`.
- **GUI**: `je_load_density.gui.main_window.LoadDensityUI` (`python -m je_load_density.gui.main_window`);
  embeddable `je_load_density.gui.main_widget.LoadDensityWidget`.
- **Packaging**: `pyproject.toml` (stable) and `dev.toml` (`je_load_density_dev`) differ only in name and
  version; `test/test_dev_toml_parity.py` keeps the scripts, extras, dependencies and tool settings in step.
- **Release channels**, both published to PyPI by CI:
  - stable, `je_load_density`: `publish-pypi.yml` runs after `CI Stable` passes on a push to `main`. It bumps
    the patch version in `pyproject.toml`, uploads, pushes the bump to `main`, tags it and creates the GitHub
    release;
  - dev, `je_load_density_dev`: the `publish-dev` job of `ci-dev.yml` runs after `test` on a push to `dev`. It
    builds from `dev.toml` and uploads when the commit is still the tip of `dev` and the wheel differs from
    the newest published one. `scripts/dev_release.py` takes the version from PyPI (newest release plus one
    patch), so nothing is committed back and the version in `dev.toml` is only a floor;
  - both jobs hold the PyPI token and install nothing but `.github/requirements/publish.txt` (`build`, `twine`,
    `tomlkit` for the stable bump, and the build backend `setuptools`): wheels only, at locked hashes,
    generated from `publish.in` beside it. They build with `python -m build --no-isolation`, so the backend is
    the locked `setuptools` and not a fresh download. `test/test_workflow_actions.py` fails when either job
    runs any other `pip install` or an isolated build, or when the lock no longer satisfies
    `build-system.requires` in `pyproject.toml` or `dev.toml`.

## 4. Main flows

**Action file → load test → report**

```
action JSON → __main__ (run / -e) → read_action_json → Executor.execute_action
  → event_dict["LD_start_test"] = start_test(user_detail_dict, user_count, spawn_rate, test_time, tasks=…)
  → _USER_REGISTRY[user] → set_wrapper_<type>_user → locust_wrapper_proxy.user_dict[<type>].configure(...)
  → prepare_env → Locust Environment + runner → <Type>UserWrapper @task → run_scenario / execute_tasks
  → Locust request event → request_hook → test_record_instance
  → LD_generate_*_report | LD_evaluate_sla | LD_persist_records
```

**Remote control**: TCP client → `start_load_density_socket_server` (optional token, framing, TLS) →
`execute_action` → results, then the terminator. **Editor tooling**: action JSON → `action_lsp` → `lint_action` (`utils/linter/action_linter.py`) →
diagnostics. Completion, `_known_commands()` in the linter, `utils/schema/action_schema.py` and the
MCP `load_density.list_executor_commands` tool all read the `LD_*` names from `executor.event_dict`.

## 5. Extension points

- **New executor command**: implement it in `utils/<area>/` → add `"LD_<name>"` in `Executor.__init__`
  (`utils/executor/action_executor.py`); the linter, schema, LSP and MCP pick it up automatically →
  export from `je_load_density/__init__.py` and `__all__` → `test/test_<area>.py`. At runtime, use
  `add_command_to_executor` (functions and methods only) or `LD_add_package_to_executor`. For callback
  triggers, also add it to `CallbackFunctionExecutor.event_dict` (`utils/callback/callback_function_executor.py`).
- **New protocol user type**, in this order:
  1. `wrapper/proxy/user/<proto>_user_proxy.py` with a proxy class exposing `configure(user_detail_dict, tasks=…, **kwargs)`.
  2. Register it in `LocustUserProxy.user_dict` (`wrapper/proxy/proxy_user.py`).
  3. `wrapper/user_template/<proto>_user_template.py` with `set_wrapper_<proto>_user` and `<Proto>UserWrapper`.
     Import the client library lazily. Fire events through `_common.fire_request_event` or subclass
     `_protocol_base.ProtocolUserBase`. `host` and `connection` given to the setter are defaults for
     the steps, and a value named in the step wins: read them with `_common.default_host` and
     `_common.with_connection_defaults` (`ProtocolUserBase` already merges `connection`). A template
     that drives an asyncio client runs it with `_common.run_template_coroutine` or on a
     `_common.new_template_event_loop()` loop, not `asyncio.run` or `asyncio.new_event_loop()`: under
     Locust on Windows, a plain loop's host name lookup never returns.
  4. Add `"<proto>_user"` to `_USER_REGISTRY` in `wrapper/start_wrapper/start_test.py`.
  5. Add an extra in `pyproject.toml` (and to `all`), then tests (`test/test_new_user_templates.py`,
     `test/test_proxy_user.py`).
- **New report**: `utils/generate_report/generate_<fmt>_report.py` reading `test_record_instance` →
  `LD_generate_<fmt>_report` command → facade export → tests.
- **MCP tool / CLI subcommand**: a `_tool_<name>` handler plus a `_TOOLS` entry (`mcp_server/server.py`);
  `_cmd_<name>` plus a subparser in `_build_parser()` (`__main__.py`), keeping the legacy flags.

## 6. Cross-project boundaries

`utils.test_record.window_statistics` supplies shared request-start buckets for
Qt, browser and PNG percentile bands. It merges success/failure samples, leaves
unmeasured windows null and counts timed requests using actual bucket duration.
Window percentiles use rounded order statistics; existing aggregate summary keys
and interpolation remain compatible. Dashboard snapshots add `latency_windows`
and retain legacy keys. Live charts bound history to 120 buckets; offline defaults
to 10,000. Protocol events convert monotonic duration clocks to epoch starts.
The responsive dashboard uses SVG/text nodes and a threaded SSE server.

Locust master/worker runs use scoped native heartbeat settings and rebalancing.
Startup defaults to failing an unmet healthy ready-worker count; explicit degraded
policy still requires one worker. Master results add `distributed_health`; this is
infrastructure health, separate from target request outcomes. `prepare_env` owns
runner/UI/RPC/auxiliary cleanup, including callback failures during ramp-up;
direct `create_env` callers own `cleanup_env`. Lifecycle callbacks are
`on_environment(env)` and `stop_requested()`. No finite-work leases, request replay
or canonical worker-record aggregation are exposed.

CLI execution retains legacy flags and Python executor return shapes, but now returns a nonzero process exit code after failed actions/SLA gates. `test/smoke` runs real HTTP/report/dashboard/MCP checks in subprocesses against source or an installed wheel. Native async HTTP benchmarking requires base httpx; the `http2` extra adds HTTP/2 support.
CI derives its Docker installation matrix from declared extras, runs isolated installed-wheel capabilities and smoke checks, and gates publishing on the reusable extras workflow. Compose probes measure Redis/MQTT adapter calls after health checks. The etcd adapter prefers etcd3gw (v3 HTTP gateway) while retaining legacy etcd3 support; this avoids incompatible generated protobuf code in the old extra.

Canonical persistence exports `persist_canonical_records(database_path, context)` and `fetch_canonical_records(database_path, run_id)` from `utils.test_record.sqlite_persistence`. Versioned tables are separate from legacy runs; transaction rollback, run-scoped JSON-aware retry conflicts and read-time schema/identity validation preserve the shared contract.

Canonical request records are an opt-in contract supplied by ActionCore's ``request_record``/
``request_context`` APIs. ``utils/test_record/contract.py`` adapts legacy results and
``run_context.py`` exposes explicit run scopes. Locust environments bind the selected context
to isolated events; asyncio propagates it to its tasks. Canonical APIs require the coordinated
core release/checkouts, while existing imports and legacy report shapes remain compatible with
the published dependency floor. The old action-executor record contract is separate and unchanged.

- **PyBreeze (subprocess)** runs `python -m je_load_density --execute_str <json>` or `--execute_file <path>`
  (`PyBreeze/pybreeze/extend/process_executor/python_task_process_manager.py`; the package name is in
  `.../process_executor/load_density/load_density_process.py`). The hidden legacy flags and the
  Windows double-encoded JSON handling in `_cmd_run_str` are a contract, guarded by
  `test/test_legacy_cli_contract.py`.
- **PyBreeze (in-process)** embeds `je_load_density.gui.main_widget.LoadDensityWidget`
  (`pybreeze/pybreeze_ui/menu/automation_menu/load_density_menu/build_load_density_menu.py`) and
  generates scripts that use `from je_load_density import start_test` (`pybreeze/utils/curl_import/script_templates.py`).
- **TestPioneer**: `with: load-runner` imports `je_load_density.execute_action` in-process
  (`test_pioneer/executor/run/utils.py`) after setting `LOCUST_SKIP_MONKEY_PATCH=1`. `parallel_run`
  spawns `python -m je_load_density --execute_file <script>` (`parallel_run.py`). Anyone embedding
  this package must keep gevent patching in mind; the socket server calls `monkey.patch_all()`.
- **APITestka (subprocess)**: `apitestka load run` / `AT_run_load_test`
  (`APITestka/je_api_testka/integrations/load_density_runner.py`) runs `python -m je_load_density --execute_file <file>`
  with the file's folder as cwd and reads the result back from the summary, not from the exit code. It relies on:
  the `{"load_density": [...]}` file shape; `LD_start_test` with `user_detail_dict.user` (`fast_http_user`,
  `http_user`), `tasks: {"mode": "sequence"|"weighted", "tasks": [...]}`, `user_count`, `spawn_rate`, `test_time`;
  the task keys `method`, `request_url` (absolute), `name`, `params`, `headers`, `cookies`, `json`, `data`,
  `timeout`, `allow_redirects`, `verify` and `assertions: [{"type": "status_code", "value": N}]`
  (`APITestka/je_api_testka/integrations/load_density.py`); and `LD_generate_summary_report(report_name)`
  writing `<report_name>.json` with `totals.requests`, `totals.failure_rate` and `latency_overall.p95_ms`.
  Renaming any of these breaks APITestka silently; change its bridge in the same round.
- **ActionCore (this repo depends on it)**: `je_action_core` (Integration-Automation/ActionCore) holds the executor,
  registry, package manager, callback executor and action-file reading and writing. LoadDensity configures them as
  follows:
  - **executor**: document key `load_density`, `executor_list_error` for every bad list, `LegacyActionParser` with
    `executor_data_error`, plain record keys, `PrintReporter` (a failure's repr and action to stderr, every record to
    stdout);
  - **registry**: functions only, refused with `LoadDensityTestExecuteException`;
  - **package manager**: bare member names, functions only, ASCII dotted names, gate on (refusals raise
    `LoadDensityTestExecuteException`; `executor.allow_packages` / `set_allow_arbitrary_packages` are the
    Python-only switches), errors printed;
  - **callback executor**: legacy checks, errors printed and raised;
  - **JSON files**: every error wrapped;
  - **socket server**: `EnvelopeTokenRequestHandler` with `socket_server_settings(framed, token, certfile, keyfile)`.
    It is raw or 4-byte length-prefixed, compares the envelope token in constant time, and wraps TLS 1.2 or later.
    Replies are one line per record, `Error: <text>` failures and `Server shutting down`; the log line names only
    the request's size. `start_load_density_socket_server` calls `monkey.patch_all()`, then blocks on
    `close_event`.

  `get_dir_files_as_list` stays here. It is a PyPI dependency (`je_action_core>=0.0.2`, also in `requirements.txt`
  / `dev_requirements.txt`, which the CI installs). ActionCore lists LoadDensity in its own §6.
- **Sibling executors** share the action-list shape and the `Return_Data_Over_JE` terminator. Builtins
  policy is now the same allowlist here, in MailThunder and in WebRunner (`SAFE_BUILTINS`, 22 names);
  APITestka, FileAutomation, AutoControlGUI and TestPioneer register no builtins at all
  (workspace `progress.md` X-12).

Cloud launchers preflight counts/resources and distinguish accepted submissions from successful execution/provisioning. Public cloud.CloudLaunchError retains accepted worker responses and failure indices. Cloud Run per-run parallelism is rejected (configure the deployed Job); ACI waits its poller and returns unique names/resource IDs. No adapter retries or rolls back launches.

Public package exports and executor command functions resolve their fixed module bindings
on first use. Importing the package, CLI parser or native HTTP engine does not load Locust
or patch socket/TLS/threading. Selecting a Locust environment registers its request hook.
`get_resolver`, `use_resolver` and `register_session_variable` are public APIs. HTTP user
templates fork variable/session state once per user; ContextVar scopes restore selection,
while locked CSV/DB providers allocate one coherent row per recursive task resolution.
CLI action failures are counted through a scoped reporter around public execute_action;
report callbacks and settings restoration do not require the unreleased core collector API.

The public start_test signature remains compatible and accepts engine through kwargs:
locust defaults to the existing environment path, asyncio dispatches local native HTTP.
AsyncRunHandle owns clients/tasks, user resolvers, run summary and cooperative callbacks;
retiring workers retain explicit stop intent through transport cancellation scopes,
including load-shape downsizing, retry and journey-step boundaries. The existing
legacy record/report and canonical opt-in paths remain available. Unsupported protocols,
distributed options and exporter integrations are retained as outstanding capabilities.
The desktop Qt supervisor communicates with a fresh engine interpreter through bounded
JSON frames and a unique cancellation file; no worker mutates Qt objects. Existing PyBreeze
LoadDensityWidget controls and tab attributes remain available.
The 128 KiB frame budget retains recent complete request rows; charts consume at most
120 child-computed windows covering full measurements rather than the bounded row tail.

Locust master opt-in DistributedRunContext composes public strict ActionCore worker contexts.
Worker distributed_records delivery binds producer epochs/generations to master run identity,
uses bounded sequenced batches with ACK retry and final drain, and preserves record IDs across
reconnection. Master whole-batch validation and global deduplication feed legacy reports once.
env.record_delivery exposes pending/incomplete diagnostics; failure cleanup preserves caller
exceptions. No durable queue, finite shard replay, session migration or HTTP exactly-once promise
is part of this native ongoing-load contract. Legacy start-wrapper imports now defer the Locust
implementation to locust_start.py while preserving the original registry/import attributes.

## 7. Design constraints

- SOLID, composition over inheritance, patterns only where they reduce complexity (CLAUDE.md
  § Coding Standards › Design Patterns & Software Engineering). No unused code, stubs or
  commented-out code (§ Code Hygiene).
- Security: no `eval`/`exec`/`__import__`/`pickle.loads` on untrusted input; `yaml.safe_load` only;
  `subprocess` with argument lists; validate paths against traversal; explicit timeouts on requests
  and sockets; never log secrets (§ Security; § Linter Compliance › Security).
- Limits: cognitive complexity ≤ 15, cyclomatic complexity ≤ 10, functions ≤ 80 lines, files ≤ 1000
  lines, ≤ 7 parameters, nesting ≤ 4. The parameter limit is why `start_test` takes its distributed-mode
  fields through `**kwargs` (§ Linter Compliance › Complexity & Structure).
- Type hints on public functions; `@dataclass` / `TypedDict` / `Enum` over ad-hoc dicts (§ Type Safety
  & API Design). Deterministic tests that mock network, filesystem and subprocess (§ Testing Hygiene).
- Conventional-commit prefixes, imperative mood, subject under 72 characters (§ Git Commit Rules).

## 8. When to update this file

- A package under `je_load_density/` or a top-level directory is added, removed or renamed.
- CLI subcommands, legacy flags, `[project.scripts]` or the MCP/LSP/socket entry points change.
- The action format (`load_density` key, `LD_` prefix), `_USER_REGISTRY` / `LocustUserProxy` wiring,
  the record → report path, or a §6 contract (PyBreeze/TestPioneer invocation, `LoadDensityWidget`,
  monkey-patch handling, builtins policy) changes.
- A CLAUDE.md section referenced in §7 is renamed or its rule changes.
- Refresh the "Last verified" line whenever this file is re-checked against HEAD.
