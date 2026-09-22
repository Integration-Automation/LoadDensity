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
from je_load_density.utils.generate_report.generate_allure_report import (
    generate_allure_report,
)
from je_load_density.utils.generate_report.generate_chart_report import (
    generate_chart_report,
)
from je_load_density.utils.generate_report.generate_histogram_report import (
    generate_histogram_report,
)
from je_load_density.utils.generate_report.generate_pdf_report import (
    generate_pdf_report,
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

# JSON / YAML / TOML IO
from je_load_density.utils.json.json_file.json_file import read_action_json
from je_load_density.utils.json.json_file.toml_file import (
    read_action_toml,
    write_action_toml,
)
from je_load_density.utils.json.json_file.yaml_file import (
    read_action_yaml,
    write_action_yaml,
)

# Metrics
from je_load_density.utils.metrics import (
    start_influxdb_sink,
    start_opentelemetry_exporter,
    start_prometheus_exporter,
    stop_influxdb_sink,
    stop_opentelemetry_exporter,
    stop_prometheus_exporter,
)
from je_load_density.utils.metrics.datadog_apm_exporter import (
    start_datadog_apm_exporter,
    stop_datadog_apm_exporter,
)
from je_load_density.utils.metrics.opentelemetry_tracing_exporter import (
    start_opentelemetry_tracing_exporter,
    stop_opentelemetry_tracing_exporter,
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
from je_load_density.utils.action_generator.generate import (
    generate_from_curls,
    generate_from_openapi,
    merge_actions,
)
from je_load_density.utils.ci_annotations.github_actions import (
    emit_github_annotations,
    format_github_annotation,
)
from je_load_density.utils.linter.action_formatter import (
    format_action_document,
    format_action_file,
    format_action_string,
)
from je_load_density.utils.linter.action_linter import lint_action, lint_action_file
from je_load_density.utils.schema.action_schema import (
    action_json_schema,
    export_schema,
)

# SLA / regression
from je_load_density.utils.regression.diff import diff_runs, summarise_records
from je_load_density.utils.regression.error_clustering import cluster_errors
from je_load_density.utils.regression.multi_run_trend import trend_runs
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
from je_load_density.utils.notifier.gitlab import (
    build_gitlab_mr_note,
    post_gitlab_mr_summary,
)
from je_load_density.utils.notifier.opsgenie import (
    build_opsgenie_alert,
    post_opsgenie_alert,
)
from je_load_density.utils.notifier.pagerduty import (
    build_pagerduty_event,
    post_pagerduty_event,
)
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

# Scenario / Security / Stub / Chaos
from je_load_density.utils.chaos.chaos_mesh import (
    apply_manifest as chaos_apply_manifest,
    build_network_delay as chaos_build_network_delay,
    delete_manifest as chaos_delete_manifest,
)
from je_load_density.utils.chaos.toxiproxy import (
    add_toxic as toxiproxy_add_toxic,
    create_proxy as toxiproxy_create_proxy,
    install_bandwidth as toxiproxy_install_bandwidth,
    install_latency as toxiproxy_install_latency,
    list_proxies as toxiproxy_list_proxies,
    remove_proxies as toxiproxy_remove_proxies,
    remove_toxic as toxiproxy_remove_toxic,
    reset_all as toxiproxy_reset_all,
)
from je_load_density.utils.scenario.cookie_jar import (
    jar_for_user,
    reset_all_jars,
    reset_user_jar,
)
from je_load_density.utils.scenario.fsm import FsmRunner
from je_load_density.utils.security.fuzz import (
    expand_task_fuzz,
    fuzz_query_string,
    mutate_json,
    mutate_string,
)
from je_load_density.utils.security.owasp_checks import (
    check_broken_object_level_auth,
    check_excessive_data_exposure,
    check_security_headers,
    check_sensitive_token_leak,
    run_owasp_checks,
)
from je_load_density.utils.stub_server.stub_server import (
    start_stub_server,
    stop_stub_server,
)

# Native asyncio engine
from je_load_density.engine.asyncio_engine import run_async_load

# AI features
from je_load_density.utils.ai.auto_baseline import calibrate_sla
from je_load_density.utils.ai.auto_tune import AutoTuner
from je_load_density.utils.ai.root_cause import (
    build_root_cause_prompt,
    render_prompt_text,
)
from je_load_density.utils.ai.smart_shape import find_breaking_point

# Cloud worker adapters
from je_load_density.cloud.aws_fargate import launch_fargate_workers
from je_load_density.cloud.aws_lambda import (
    invoke_lambda_workers,
    lambda_worker_handler,
)
from je_load_density.cloud.azure_aci import launch_aci_workers
from je_load_density.cloud.gcp_cloud_run import run_cloud_run_job

# CI / canary
from je_load_density.utils.ci_annotations.canary_analysis import canary_verdict

# Data / state utilities
from je_load_density.utils.data.db_fixtures import apply_fixture, run_teardown
from je_load_density.utils.data.factory import build_user, build_user_pool
from je_load_density.utils.data.pii_anonymizer import (
    find_pii,
    scrub as pii_scrub,
    scrub_string as pii_scrub_string,
)

# DX / tooling
from je_load_density.utils.dx.i18n import (
    available_locales,
    get_current_locale,
    t as translate,
)
from je_load_density.utils.dx.leak_detector import (
    detect_growing_allocations,
    start_leak_detector,
    stop_leak_detector,
)
from je_load_density.utils.dx.profiler import memory_snapshot, profile_call
from je_load_density.utils.dx.repl import start_repl

# Governance
from je_load_density.utils.governance.audit_log import (
    append_audit_entry,
    read_audit_log,
)
from je_load_density.utils.governance.run_tagging import (
    list_tags,
    search_runs_by_tag,
    tag_run,
)
from je_load_density.utils.governance.share_link import (
    issue_share_link,
    verify_share_link,
)
from je_load_density.utils.governance.test_catalog import index_catalog, search_catalog

# Reports (additional)
from je_load_density.utils.generate_report.generate_cost_report import (
    estimate_run_cost,
    generate_cost_report,
)
from je_load_density.utils.generate_report.generate_cyclonedx_report import (
    generate_cyclonedx_report,
)
from je_load_density.utils.generate_report.generate_excel_report import (
    generate_excel_report,
)
from je_load_density.utils.generate_report.generate_sarif_report import (
    generate_sarif_report,
)
from je_load_density.utils.generate_report.generate_service_map import (
    build_service_map,
    generate_service_map,
)

# Recording (additional)
from je_load_density.utils.recording.cdp_capture import (
    capture_cdp_session,
    capture_cdp_to_har,
    discover_targets as cdp_discover_targets,
)

# Security: extended attack toolkits
from je_load_density.utils.security.graphql_checks import (
    build_alias_batching_attack,
    build_depth_attack,
    build_introspection_payload,
    graphql_attack_pack,
)
from je_load_density.utils.security.jwt_attacks import (
    craft_alg_confusion_token,
    craft_alg_none_token,
    craft_attack_pack as craft_jwt_attack_pack,
    craft_expired_token,
    craft_kid_traversal_token,
)
from je_load_density.utils.security.rate_limit_probe import probe_rate_limit
from je_load_density.utils.security.smuggling_checks import (
    build_cl_te,
    build_te_cl,
    build_te_te,
    smuggling_attack_pack,
)
from je_load_density.utils.security.ssrf_checks import (
    build_ssrf_targets,
    find_metadata_leak,
    render_ssrf_tasks,
)

# Tracing exporters

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
    # New report formats
    "generate_histogram_report", "generate_pdf_report", "generate_allure_report",
    # YAML / TOML loaders
    "read_action_yaml", "write_action_yaml",
    "read_action_toml", "write_action_toml",
    # Tracing & APM exporters
    "start_opentelemetry_tracing_exporter", "stop_opentelemetry_tracing_exporter",
    "start_datadog_apm_exporter", "stop_datadog_apm_exporter",
    # Notifier
    "post_pagerduty_event", "build_pagerduty_event",
    "post_opsgenie_alert", "build_opsgenie_alert",
    "post_gitlab_mr_summary", "build_gitlab_mr_note",
    # Trend & error clustering
    "trend_runs", "cluster_errors",
    # DX
    "format_action_document", "format_action_file", "format_action_string",
    "generate_from_openapi", "generate_from_curls", "merge_actions",
    # Scenario
    "FsmRunner", "jar_for_user", "reset_user_jar", "reset_all_jars",
    # Stub server
    "start_stub_server", "stop_stub_server",
    # Security
    "mutate_string", "mutate_json", "fuzz_query_string", "expand_task_fuzz",
    "run_owasp_checks",
    "check_broken_object_level_auth", "check_excessive_data_exposure",
    "check_security_headers", "check_sensitive_token_leak",
    # Chaos
    "toxiproxy_create_proxy", "toxiproxy_list_proxies",
    "toxiproxy_add_toxic", "toxiproxy_remove_toxic",
    "toxiproxy_install_latency", "toxiproxy_install_bandwidth",
    "toxiproxy_reset_all", "toxiproxy_remove_proxies",
    "chaos_apply_manifest", "chaos_delete_manifest", "chaos_build_network_delay",
    # Asyncio engine
    "run_async_load",
    # AI
    "AutoTuner", "build_root_cause_prompt", "render_prompt_text",
    "find_breaking_point", "calibrate_sla",
    # Cloud workers
    "invoke_lambda_workers", "lambda_worker_handler",
    "launch_fargate_workers", "launch_aci_workers", "run_cloud_run_job",
    # CI / canary
    "canary_verdict",
    # Data / state
    "apply_fixture", "run_teardown",
    "build_user", "build_user_pool",
    "pii_scrub", "pii_scrub_string", "find_pii",
    # DX
    "start_repl", "profile_call", "memory_snapshot",
    "start_leak_detector", "stop_leak_detector", "detect_growing_allocations",
    "translate", "available_locales", "get_current_locale",
    # Governance
    "append_audit_entry", "read_audit_log",
    "tag_run", "list_tags", "search_runs_by_tag",
    "issue_share_link", "verify_share_link",
    "index_catalog", "search_catalog",
    # Reports (additional)
    "generate_excel_report", "generate_sarif_report", "generate_cyclonedx_report",
    "generate_service_map", "build_service_map",
    "generate_cost_report", "estimate_run_cost",
    # Recording (additional)
    "cdp_discover_targets", "capture_cdp_session", "capture_cdp_to_har",
    # Security: extended
    "craft_alg_none_token", "craft_alg_confusion_token",
    "craft_expired_token", "craft_kid_traversal_token",
    "craft_jwt_attack_pack",
    "build_introspection_payload", "build_depth_attack",
    "build_alias_batching_attack", "graphql_attack_pack",
    "build_ssrf_targets", "render_ssrf_tasks", "find_metadata_leak",
    "build_cl_te", "build_te_cl", "build_te_te", "smuggling_attack_pack",
    "probe_rate_limit",
]
