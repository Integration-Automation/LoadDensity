# hook (side-effect import: registers Locust request hooks)
from je_load_density.wrapper.event.request_hook import request_hook  # noqa: F401

# Executor + action plumbing
from je_load_density.utils.executor.action_executor import (
    add_command_to_executor,
    execute_action,
    execute_files,
    executor,
)
from je_load_density.utils.file_process.get_dir_file_list import get_dir_files_as_list

# Reports
from je_load_density.utils.generate_report.generate_chart_report import (
    generate_chart_report,
)
from je_load_density.utils.generate_report.generate_csv_report import generate_csv_report
from je_load_density.utils.generate_report.generate_html_report import (
    generate_html,
    generate_html_report,
)
from je_load_density.utils.generate_report.generate_json_report import (
    generate_json,
    generate_json_report,
)
from je_load_density.utils.generate_report.generate_junit_report import generate_junit_report
from je_load_density.utils.generate_report.generate_summary_report import (
    build_summary,
    generate_summary_report,
)
from je_load_density.utils.generate_report.generate_xml_report import (
    generate_xml,
    generate_xml_report,
)

# JSON IO
from je_load_density.utils.json.json_file.json_file import read_action_json

# Metrics
from je_load_density.utils.metrics import (
    start_influxdb_sink,
    start_opentelemetry_exporter,
    start_prometheus_exporter,
    stop_influxdb_sink,
    stop_opentelemetry_exporter,
    stop_prometheus_exporter,
)

# Parameterisation
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_source,
    register_csv_sources,
    register_db_source,
    register_db_sources,
    register_variable,
    register_variables,
    resolve,
)

# Recording / replay
from je_load_density.utils.recording.curl_importer import curl_to_task
from je_load_density.utils.recording.har_importer import (
    har_to_action_json,
    har_to_tasks,
    load_har,
)
from je_load_density.utils.recording.openapi_importer import (
    load_openapi,
    openapi_to_action_json,
    openapi_to_tasks,
)
from je_load_density.utils.recording.postman_importer import (
    load_postman_collection,
    postman_to_action_json,
    postman_to_tasks,
)

# Project scaffolding
from je_load_density.utils.project.create_project_structure import create_project_dir

# Control socket
from je_load_density.utils.socket_server.load_density_socket_server import (
    start_load_density_socket_server,
)

# Test records
from je_load_density.utils.test_record.sqlite_persistence import (
    fetch_run_records,
    list_runs,
    persist_records,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance

# Locust environment + start
from je_load_density.wrapper.create_locust_env.create_locust_env import (
    create_env,
    prepare_env,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.start_wrapper.start_test import start_test

# Locust re-exports
from locust import SequentialTaskSet, TaskSet, task

# Callback executor
from je_load_density.utils.callback.callback_function_executor import callback_executor

# DX / Quality
from je_load_density.utils.ci_annotations.github_actions import (
    emit_github_annotations,
    format_github_annotation,
)
from je_load_density.utils.linter.action_linter import lint_action, lint_action_file
from je_load_density.utils.schema.action_schema import (
    action_json_schema,
    export_schema,
)

# SLA / regression
from je_load_density.utils.regression.diff import diff_runs, summarise_records
from je_load_density.utils.sla.sla_gates import assert_sla, evaluate_sla

# Load shapes
from je_load_density.utils.load_shapes.shapes import (
    SoakShape,
    SpikeShape,
    StagesShape,
    build_load_shape,
)

# GraphQL helper
from je_load_density.utils.graphql.graphql_task import (
    extract_field,
    graphql_to_http_task,
)

# Throttle
from je_load_density.utils.throttle.rps_throttle import (
    RpsThrottle,
    get_throttle,
    reset_throttles,
)

# Reliability
from je_load_density.utils.reliability.adaptive_retry import (
    AdaptiveRetryPolicy,
    classify_error,
    run_with_retry,
)
from je_load_density.utils.reliability.failure_budget import (
    CircuitOpenError,
    FailureBudget,
    install_failure_budget,
    uninstall_failure_budget,
)
from je_load_density.utils.reliability.network_conditioner import (
    NetworkConditioner,
    install_network_conditioner,
    uninstall_network_conditioner,
)
from je_load_density.utils.reliability.process_supervisor import (
    ProcessSupervisor,
    with_watchdog,
)

# Dashboard
from je_load_density.utils.dashboard.live_dashboard import (
    snapshot_metrics,
    start_dashboard,
    stop_dashboard,
)

# Notifier
from je_load_density.utils.notifier.slack import (
    build_slack_summary,
    post_slack_summary,
)
from je_load_density.utils.notifier.teams import (
    build_teams_summary,
    post_teams_summary,
)

# StatsD
from je_load_density.utils.metrics.statsd_sink import (
    start_statsd_sink,
    stop_statsd_sink,
)

# Importers (k6 + JMeter)
from je_load_density.utils.recording.jmeter_importer import (
    jmeter_to_action_json,
    jmeter_to_tasks,
    load_jmeter_jmx,
)
from je_load_density.utils.recording.k6_importer import (
    k6_script_to_action_json,
    k6_script_to_tasks,
    load_k6_script,
)

# Auth
from je_load_density.utils.auth.aws_sigv4 import sign_aws_request
from je_load_density.utils.auth.jwt_signer import decode_jwt, sign_jwt
from je_load_density.utils.auth.oauth2 import (
    OAuth2Client,
    fetch_client_credentials_token,
    fetch_password_token,
    refresh_token,
)

__all__ = [
    "create_env", "start_test",
    "locust_wrapper_proxy",
    "prepare_env",
    "test_record_instance",
    "execute_action", "execute_files", "executor", "add_command_to_executor",
    "get_dir_files_as_list",
    "generate_html", "generate_html_report",
    "generate_json", "generate_json_report",
    "generate_xml", "generate_xml_report",
    "generate_csv_report", "generate_junit_report", "generate_summary_report",
    "generate_chart_report",
    "build_summary",
    "read_action_json",
    "start_load_density_socket_server",
    "SequentialTaskSet", "task", "TaskSet",
    "callback_executor", "create_project_dir",
    "parameter_resolver", "resolve",
    "register_variable", "register_variables",
    "register_csv_source", "register_csv_sources",
    "register_db_source", "register_db_sources",
    "har_to_action_json", "har_to_tasks", "load_har",
    "postman_to_action_json", "postman_to_tasks", "load_postman_collection",
    "openapi_to_action_json", "openapi_to_tasks", "load_openapi",
    "curl_to_task",
    "persist_records", "list_runs", "fetch_run_records",
    "start_prometheus_exporter", "stop_prometheus_exporter",
    "start_influxdb_sink", "stop_influxdb_sink",
    "start_opentelemetry_exporter", "stop_opentelemetry_exporter",
    "lint_action", "lint_action_file",
    "action_json_schema", "export_schema",
    "emit_github_annotations", "format_github_annotation",
    "evaluate_sla", "assert_sla",
    "diff_runs", "summarise_records",
    "SoakShape", "SpikeShape", "StagesShape", "build_load_shape",
    "graphql_to_http_task", "extract_field",
    "RpsThrottle", "get_throttle", "reset_throttles",
    "AdaptiveRetryPolicy", "classify_error", "run_with_retry",
    "FailureBudget", "CircuitOpenError",
    "install_failure_budget", "uninstall_failure_budget",
    "NetworkConditioner",
    "install_network_conditioner", "uninstall_network_conditioner",
    "ProcessSupervisor", "with_watchdog",
    "start_dashboard", "stop_dashboard", "snapshot_metrics",
    "post_slack_summary", "build_slack_summary",
    "post_teams_summary", "build_teams_summary",
    "start_statsd_sink", "stop_statsd_sink",
    "jmeter_to_action_json", "jmeter_to_tasks", "load_jmeter_jmx",
    "k6_script_to_action_json", "k6_script_to_tasks", "load_k6_script",
    "OAuth2Client",
    "fetch_client_credentials_token", "fetch_password_token", "refresh_token",
    "sign_jwt", "decode_jwt", "sign_aws_request",
]
