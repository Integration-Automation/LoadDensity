# LoadDensity Architecture

> Short overview for people and agents.
> Last verified: 2026-09-22 against `7cf7901` on `dev`.

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
| `je_load_density/utils/executor/` | `Executor.event_dict` (`LD_*` commands plus builtins minus `_UNSAFE_BUILTINS`), `execute_action`, `execute_files`, `add_command_to_executor` |
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
| `je_load_density/gui/` | Optional PySide6 GUI (`gui` extra). `chart_panel.py` and `run_history_panel.py` are not wired into the main window yet |
| `editors/vscode/` | VS Code extension that starts the LSP. `editors/chrome-extension/` and `editors/jetbrains/` hold the Chrome and JetBrains extensions |
| `deploy/` | Helm chart, k8s operator, Terraform, Grafana dashboard, CI templates |
| `docker/`, `action.yml`, `.pre-commit-hooks.yaml`, `examples/` | docker-compose test stack, composite GitHub Action, pre-commit hook, sample actions and scripts |
| `load_density_driver/` | Prebuilt driver (script plus Windows and Linux binaries) |
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
- **MCP**: `loaddensity-mcp` or `python -m je_load_density.mcp_server` (stdio, needs the `mcp` extra).
  Tools are the `load_density.*` entries in `_TOOLS` (`mcp_server/server.py`).
- **LSP**: `loaddensity-lsp` or `python -m je_load_density.action_lsp` (stdio). `editors/vscode/extension.js`
  starts it with `-m je_load_density.action_lsp`.
- **TCP control server**: `start_load_density_socket_server(host="localhost", port=9940, framed, token, certfile, keyfile)`.
  The token can also come from `LOAD_DENSITY_SOCKET_TOKEN`. Replies end with `Return_Data_Over_JE\n`.
  Starting the server calls gevent `monkey.patch_all()`.
- **CI hooks**: `action.yml` lints, runs `python -m je_load_density run`, then emits annotations.
  `.pre-commit-hooks.yaml` runs `python -m je_load_density.tools.lint_files`.
- **GUI**: `je_load_density.gui.main_window.LoadDensityUI` (`python -m je_load_density.gui.main_window`);
  embeddable `je_load_density.gui.main_widget.LoadDensityWidget`.
- **Packaging gap**: only `pyproject.toml` declares the console scripts and the extras other than
  `gui`. `dev.toml` declares neither.

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
     `_protocol_base.ProtocolUserBase`.
  4. Add `"<proto>_user"` to `_USER_REGISTRY` in `wrapper/start_wrapper/start_test.py`.
  5. Add an extra in `pyproject.toml` (and to `all`), then tests (`test/test_new_user_templates.py`,
     `test/test_proxy_user.py`).
- **New report**: `utils/generate_report/generate_<fmt>_report.py` reading `test_record_instance` →
  `LD_generate_<fmt>_report` command → facade export → tests.
- **MCP tool / CLI subcommand**: a `_tool_<name>` handler plus a `_TOOLS` entry (`mcp_server/server.py`);
  `_cmd_<name>` plus a subparser in `_build_parser()` (`__main__.py`), keeping the legacy flags.

## 6. Cross-project boundaries

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
- **Sibling executors** share the action-list shape and the `Return_Data_Over_JE` terminator. Builtins
  policies differ: LoadDensity blacklists `_UNSAFE_BUILTINS` (`eval`, `exec`, `compile`, `__import__`,
  `breakpoint`, `open`, `input`); APITestka registers none; MailThunder registers all (known gap).

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
