"""Public APIs are loaded on demand; native asyncio imports do not patch process I/O."""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from locust import SequentialTaskSet as SequentialTaskSet
    from locust import TaskSet as TaskSet
    from locust import task as task

    from je_load_density.cloud.aws_fargate import launch_fargate_workers as launch_fargate_workers
    from je_load_density.cloud.aws_lambda import invoke_lambda_workers as invoke_lambda_workers
    from je_load_density.cloud.aws_lambda import lambda_worker_handler as lambda_worker_handler
    from je_load_density.cloud.azure_aci import launch_aci_workers as launch_aci_workers
    from je_load_density.cloud.gcp_cloud_run import run_cloud_run_job as run_cloud_run_job
    from je_load_density.engine.asyncio_engine import AsyncRunHandle as AsyncRunHandle
    from je_load_density.engine.asyncio_engine import run_async_load as run_async_load
    from je_load_density.engine.entrypoints import start_test as start_test
    from je_load_density.utils.action_generator.generate import generate_from_curls as generate_from_curls
    from je_load_density.utils.action_generator.generate import generate_from_openapi as generate_from_openapi
    from je_load_density.utils.action_generator.generate import merge_actions as merge_actions
    from je_load_density.utils.ai.auto_baseline import calibrate_sla as calibrate_sla
    from je_load_density.utils.ai.auto_tune import AutoTuner as AutoTuner
    from je_load_density.utils.ai.root_cause import build_root_cause_prompt as build_root_cause_prompt
    from je_load_density.utils.ai.root_cause import render_prompt_text as render_prompt_text
    from je_load_density.utils.ai.smart_shape import find_breaking_point as find_breaking_point
    from je_load_density.utils.auth.aws_sigv4 import sign_aws_request as sign_aws_request
    from je_load_density.utils.auth.jwt_signer import decode_jwt as decode_jwt
    from je_load_density.utils.auth.jwt_signer import sign_jwt as sign_jwt
    from je_load_density.utils.auth.oauth2 import OAuth2Client as OAuth2Client
    from je_load_density.utils.auth.oauth2 import fetch_client_credentials_token as fetch_client_credentials_token
    from je_load_density.utils.auth.oauth2 import fetch_password_token as fetch_password_token
    from je_load_density.utils.auth.oauth2 import refresh_token as refresh_token
    from je_load_density.utils.callback.callback_function_executor import callback_executor as callback_executor
    from je_load_density.utils.chaos.chaos_mesh import apply_manifest as chaos_apply_manifest
    from je_load_density.utils.chaos.chaos_mesh import build_network_delay as chaos_build_network_delay
    from je_load_density.utils.chaos.chaos_mesh import delete_manifest as chaos_delete_manifest
    from je_load_density.utils.chaos.toxiproxy import add_toxic as toxiproxy_add_toxic
    from je_load_density.utils.chaos.toxiproxy import create_proxy as toxiproxy_create_proxy
    from je_load_density.utils.chaos.toxiproxy import install_bandwidth as toxiproxy_install_bandwidth
    from je_load_density.utils.chaos.toxiproxy import install_latency as toxiproxy_install_latency
    from je_load_density.utils.chaos.toxiproxy import list_proxies as toxiproxy_list_proxies
    from je_load_density.utils.chaos.toxiproxy import remove_proxies as toxiproxy_remove_proxies
    from je_load_density.utils.chaos.toxiproxy import remove_toxic as toxiproxy_remove_toxic
    from je_load_density.utils.chaos.toxiproxy import reset_all as toxiproxy_reset_all
    from je_load_density.utils.ci_annotations.canary_analysis import canary_verdict as canary_verdict
    from je_load_density.utils.ci_annotations.github_actions import emit_github_annotations as emit_github_annotations
    from je_load_density.utils.ci_annotations.github_actions import format_github_annotation as format_github_annotation
    from je_load_density.utils.dashboard.live_dashboard import snapshot_metrics as snapshot_metrics
    from je_load_density.utils.dashboard.live_dashboard import start_dashboard as start_dashboard
    from je_load_density.utils.dashboard.live_dashboard import stop_dashboard as stop_dashboard
    from je_load_density.utils.data.db_fixtures import apply_fixture as apply_fixture
    from je_load_density.utils.data.db_fixtures import run_teardown as run_teardown
    from je_load_density.utils.data.factory import build_user as build_user
    from je_load_density.utils.data.factory import build_user_pool as build_user_pool
    from je_load_density.utils.data.pii_anonymizer import find_pii as find_pii
    from je_load_density.utils.data.pii_anonymizer import scrub as pii_scrub
    from je_load_density.utils.data.pii_anonymizer import scrub_string as pii_scrub_string
    from je_load_density.utils.dx.i18n import available_locales as available_locales
    from je_load_density.utils.dx.i18n import get_current_locale as get_current_locale
    from je_load_density.utils.dx.i18n import t as translate
    from je_load_density.utils.dx.leak_detector import detect_growing_allocations as detect_growing_allocations
    from je_load_density.utils.dx.leak_detector import start_leak_detector as start_leak_detector
    from je_load_density.utils.dx.leak_detector import stop_leak_detector as stop_leak_detector
    from je_load_density.utils.dx.profiler import memory_snapshot as memory_snapshot
    from je_load_density.utils.dx.profiler import profile_call as profile_call
    from je_load_density.utils.dx.repl import start_repl as start_repl
    from je_load_density.utils.executor.action_executor import add_command_to_executor as add_command_to_executor
    from je_load_density.utils.executor.action_executor import execute_action as execute_action
    from je_load_density.utils.executor.action_executor import execute_files as execute_files
    from je_load_density.utils.executor.action_executor import executor as executor
    from je_load_density.utils.file_process.get_dir_file_list import get_dir_files_as_list as get_dir_files_as_list
    from je_load_density.utils.generate_report.generate_allure_report import (
        generate_allure_report as generate_allure_report,
    )
    from je_load_density.utils.generate_report.generate_chart_report import (
        generate_chart_report as generate_chart_report,
    )
    from je_load_density.utils.generate_report.generate_cost_report import estimate_run_cost as estimate_run_cost
    from je_load_density.utils.generate_report.generate_cost_report import generate_cost_report as generate_cost_report
    from je_load_density.utils.generate_report.generate_csv_report import generate_csv_report as generate_csv_report
    from je_load_density.utils.generate_report.generate_cyclonedx_report import (
        generate_cyclonedx_report as generate_cyclonedx_report,
    )
    from je_load_density.utils.generate_report.generate_excel_report import (
        generate_excel_report as generate_excel_report,
    )
    from je_load_density.utils.generate_report.generate_histogram_report import (
        generate_histogram_report as generate_histogram_report,
    )
    from je_load_density.utils.generate_report.generate_html_report import generate_html as generate_html
    from je_load_density.utils.generate_report.generate_html_report import generate_html_report as generate_html_report
    from je_load_density.utils.generate_report.generate_json_report import generate_json as generate_json
    from je_load_density.utils.generate_report.generate_json_report import generate_json_report as generate_json_report
    from je_load_density.utils.generate_report.generate_junit_report import (
        generate_junit_report as generate_junit_report,
    )
    from je_load_density.utils.generate_report.generate_pdf_report import generate_pdf_report as generate_pdf_report
    from je_load_density.utils.generate_report.generate_sarif_report import (
        generate_sarif_report as generate_sarif_report,
    )
    from je_load_density.utils.generate_report.generate_service_map import build_service_map as build_service_map
    from je_load_density.utils.generate_report.generate_service_map import generate_service_map as generate_service_map
    from je_load_density.utils.generate_report.generate_summary_report import build_summary as build_summary
    from je_load_density.utils.generate_report.generate_summary_report import (
        generate_summary_report as generate_summary_report,
    )
    from je_load_density.utils.generate_report.generate_xml_report import generate_xml as generate_xml
    from je_load_density.utils.generate_report.generate_xml_report import generate_xml_report as generate_xml_report
    from je_load_density.utils.governance.audit_log import append_audit_entry as append_audit_entry
    from je_load_density.utils.governance.audit_log import read_audit_log as read_audit_log
    from je_load_density.utils.governance.run_tagging import list_tags as list_tags
    from je_load_density.utils.governance.run_tagging import search_runs_by_tag as search_runs_by_tag
    from je_load_density.utils.governance.run_tagging import tag_run as tag_run
    from je_load_density.utils.governance.share_link import issue_share_link as issue_share_link
    from je_load_density.utils.governance.share_link import verify_share_link as verify_share_link
    from je_load_density.utils.governance.test_catalog import index_catalog as index_catalog
    from je_load_density.utils.governance.test_catalog import search_catalog as search_catalog
    from je_load_density.utils.graphql.graphql_task import extract_field as extract_field
    from je_load_density.utils.graphql.graphql_task import graphql_to_http_task as graphql_to_http_task
    from je_load_density.utils.json.json_file.json_file import read_action_json as read_action_json
    from je_load_density.utils.json.json_file.toml_file import read_action_toml as read_action_toml
    from je_load_density.utils.json.json_file.toml_file import write_action_toml as write_action_toml
    from je_load_density.utils.json.json_file.yaml_file import read_action_yaml as read_action_yaml
    from je_load_density.utils.json.json_file.yaml_file import write_action_yaml as write_action_yaml
    from je_load_density.utils.linter.action_formatter import format_action_document as format_action_document
    from je_load_density.utils.linter.action_formatter import format_action_file as format_action_file
    from je_load_density.utils.linter.action_formatter import format_action_string as format_action_string
    from je_load_density.utils.linter.action_linter import lint_action as lint_action
    from je_load_density.utils.linter.action_linter import lint_action_file as lint_action_file
    from je_load_density.utils.load_shapes.shapes import SoakShape as SoakShape
    from je_load_density.utils.load_shapes.shapes import SpikeShape as SpikeShape
    from je_load_density.utils.load_shapes.shapes import StagesShape as StagesShape
    from je_load_density.utils.load_shapes.shapes import build_load_shape as build_load_shape
    from je_load_density.utils.metrics import start_influxdb_sink as start_influxdb_sink
    from je_load_density.utils.metrics import start_opentelemetry_exporter as start_opentelemetry_exporter
    from je_load_density.utils.metrics import start_prometheus_exporter as start_prometheus_exporter
    from je_load_density.utils.metrics import stop_influxdb_sink as stop_influxdb_sink
    from je_load_density.utils.metrics import stop_opentelemetry_exporter as stop_opentelemetry_exporter
    from je_load_density.utils.metrics import stop_prometheus_exporter as stop_prometheus_exporter
    from je_load_density.utils.metrics.datadog_apm_exporter import (
        start_datadog_apm_exporter as start_datadog_apm_exporter,
    )
    from je_load_density.utils.metrics.datadog_apm_exporter import (
        stop_datadog_apm_exporter as stop_datadog_apm_exporter,
    )
    from je_load_density.utils.metrics.opentelemetry_tracing_exporter import (
        start_opentelemetry_tracing_exporter as start_opentelemetry_tracing_exporter,
    )
    from je_load_density.utils.metrics.opentelemetry_tracing_exporter import (
        stop_opentelemetry_tracing_exporter as stop_opentelemetry_tracing_exporter,
    )
    from je_load_density.utils.metrics.statsd_sink import start_statsd_sink as start_statsd_sink
    from je_load_density.utils.metrics.statsd_sink import stop_statsd_sink as stop_statsd_sink
    from je_load_density.utils.notifier.gitlab import build_gitlab_mr_note as build_gitlab_mr_note
    from je_load_density.utils.notifier.gitlab import post_gitlab_mr_summary as post_gitlab_mr_summary
    from je_load_density.utils.notifier.opsgenie import build_opsgenie_alert as build_opsgenie_alert
    from je_load_density.utils.notifier.opsgenie import post_opsgenie_alert as post_opsgenie_alert
    from je_load_density.utils.notifier.pagerduty import build_pagerduty_event as build_pagerduty_event
    from je_load_density.utils.notifier.pagerduty import post_pagerduty_event as post_pagerduty_event
    from je_load_density.utils.notifier.slack import build_slack_summary as build_slack_summary
    from je_load_density.utils.notifier.slack import post_slack_summary as post_slack_summary
    from je_load_density.utils.notifier.teams import build_teams_summary as build_teams_summary
    from je_load_density.utils.notifier.teams import post_teams_summary as post_teams_summary
    from je_load_density.utils.parameterization import get_resolver as get_resolver
    from je_load_density.utils.parameterization import parameter_resolver as parameter_resolver
    from je_load_density.utils.parameterization import register_csv_source as register_csv_source
    from je_load_density.utils.parameterization import register_csv_sources as register_csv_sources
    from je_load_density.utils.parameterization import register_db_source as register_db_source
    from je_load_density.utils.parameterization import register_db_sources as register_db_sources
    from je_load_density.utils.parameterization import register_session_variable as register_session_variable
    from je_load_density.utils.parameterization import register_variable as register_variable
    from je_load_density.utils.parameterization import register_variables as register_variables
    from je_load_density.utils.parameterization import resolve as resolve
    from je_load_density.utils.parameterization import use_resolver as use_resolver
    from je_load_density.utils.project.create_project_structure import create_project_dir as create_project_dir
    from je_load_density.utils.recording.cdp_capture import capture_cdp_session as capture_cdp_session
    from je_load_density.utils.recording.cdp_capture import capture_cdp_to_har as capture_cdp_to_har
    from je_load_density.utils.recording.cdp_capture import discover_targets as cdp_discover_targets
    from je_load_density.utils.recording.curl_importer import curl_to_task as curl_to_task
    from je_load_density.utils.recording.har_importer import har_to_action_json as har_to_action_json
    from je_load_density.utils.recording.har_importer import har_to_tasks as har_to_tasks
    from je_load_density.utils.recording.har_importer import load_har as load_har
    from je_load_density.utils.recording.jmeter_importer import jmeter_to_action_json as jmeter_to_action_json
    from je_load_density.utils.recording.jmeter_importer import jmeter_to_tasks as jmeter_to_tasks
    from je_load_density.utils.recording.jmeter_importer import load_jmeter_jmx as load_jmeter_jmx
    from je_load_density.utils.recording.k6_importer import k6_script_to_action_json as k6_script_to_action_json
    from je_load_density.utils.recording.k6_importer import k6_script_to_tasks as k6_script_to_tasks
    from je_load_density.utils.recording.k6_importer import load_k6_script as load_k6_script
    from je_load_density.utils.recording.openapi_importer import load_openapi as load_openapi
    from je_load_density.utils.recording.openapi_importer import openapi_to_action_json as openapi_to_action_json
    from je_load_density.utils.recording.openapi_importer import openapi_to_tasks as openapi_to_tasks
    from je_load_density.utils.recording.postman_importer import load_postman_collection as load_postman_collection
    from je_load_density.utils.recording.postman_importer import postman_to_action_json as postman_to_action_json
    from je_load_density.utils.recording.postman_importer import postman_to_tasks as postman_to_tasks
    from je_load_density.utils.regression.diff import diff_runs as diff_runs
    from je_load_density.utils.regression.diff import summarise_records as summarise_records
    from je_load_density.utils.regression.error_clustering import cluster_errors as cluster_errors
    from je_load_density.utils.regression.multi_run_trend import trend_runs as trend_runs
    from je_load_density.utils.reliability.adaptive_retry import AdaptiveRetryPolicy as AdaptiveRetryPolicy
    from je_load_density.utils.reliability.adaptive_retry import classify_error as classify_error
    from je_load_density.utils.reliability.adaptive_retry import run_with_retry as run_with_retry
    from je_load_density.utils.reliability.failure_budget import CircuitOpenError as CircuitOpenError
    from je_load_density.utils.reliability.failure_budget import FailureBudget as FailureBudget
    from je_load_density.utils.reliability.failure_budget import install_failure_budget as install_failure_budget
    from je_load_density.utils.reliability.failure_budget import uninstall_failure_budget as uninstall_failure_budget
    from je_load_density.utils.reliability.network_conditioner import NetworkConditioner as NetworkConditioner
    from je_load_density.utils.reliability.network_conditioner import (
        install_network_conditioner as install_network_conditioner,
    )
    from je_load_density.utils.reliability.network_conditioner import (
        uninstall_network_conditioner as uninstall_network_conditioner,
    )
    from je_load_density.utils.reliability.process_supervisor import ProcessSupervisor as ProcessSupervisor
    from je_load_density.utils.reliability.process_supervisor import with_watchdog as with_watchdog
    from je_load_density.utils.scenario.cookie_jar import jar_for_user as jar_for_user
    from je_load_density.utils.scenario.cookie_jar import reset_all_jars as reset_all_jars
    from je_load_density.utils.scenario.cookie_jar import reset_user_jar as reset_user_jar
    from je_load_density.utils.scenario.fsm import FsmRunner as FsmRunner
    from je_load_density.utils.schema.action_schema import action_json_schema as action_json_schema
    from je_load_density.utils.schema.action_schema import export_schema as export_schema
    from je_load_density.utils.security.fuzz import expand_task_fuzz as expand_task_fuzz
    from je_load_density.utils.security.fuzz import fuzz_query_string as fuzz_query_string
    from je_load_density.utils.security.fuzz import mutate_json as mutate_json
    from je_load_density.utils.security.fuzz import mutate_string as mutate_string
    from je_load_density.utils.security.graphql_checks import build_alias_batching_attack as build_alias_batching_attack
    from je_load_density.utils.security.graphql_checks import build_depth_attack as build_depth_attack
    from je_load_density.utils.security.graphql_checks import build_introspection_payload as build_introspection_payload
    from je_load_density.utils.security.graphql_checks import graphql_attack_pack as graphql_attack_pack
    from je_load_density.utils.security.jwt_attacks import craft_alg_confusion_token as craft_alg_confusion_token
    from je_load_density.utils.security.jwt_attacks import craft_alg_none_token as craft_alg_none_token
    from je_load_density.utils.security.jwt_attacks import craft_attack_pack as craft_jwt_attack_pack
    from je_load_density.utils.security.jwt_attacks import craft_expired_token as craft_expired_token
    from je_load_density.utils.security.jwt_attacks import craft_kid_traversal_token as craft_kid_traversal_token
    from je_load_density.utils.security.owasp_checks import (
        check_broken_object_level_auth as check_broken_object_level_auth,
    )
    from je_load_density.utils.security.owasp_checks import (
        check_excessive_data_exposure as check_excessive_data_exposure,
    )
    from je_load_density.utils.security.owasp_checks import check_security_headers as check_security_headers
    from je_load_density.utils.security.owasp_checks import check_sensitive_token_leak as check_sensitive_token_leak
    from je_load_density.utils.security.owasp_checks import run_owasp_checks as run_owasp_checks
    from je_load_density.utils.security.rate_limit_probe import probe_rate_limit as probe_rate_limit
    from je_load_density.utils.security.smuggling_checks import build_cl_te as build_cl_te
    from je_load_density.utils.security.smuggling_checks import build_te_cl as build_te_cl
    from je_load_density.utils.security.smuggling_checks import build_te_te as build_te_te
    from je_load_density.utils.security.smuggling_checks import smuggling_attack_pack as smuggling_attack_pack
    from je_load_density.utils.security.ssrf_checks import build_ssrf_targets as build_ssrf_targets
    from je_load_density.utils.security.ssrf_checks import find_metadata_leak as find_metadata_leak
    from je_load_density.utils.security.ssrf_checks import render_ssrf_tasks as render_ssrf_tasks
    from je_load_density.utils.sla.sla_gates import assert_sla as assert_sla
    from je_load_density.utils.sla.sla_gates import evaluate_sla as evaluate_sla
    from je_load_density.utils.socket_server.load_density_socket_server import (
        start_load_density_socket_server as start_load_density_socket_server,
    )
    from je_load_density.utils.stub_server.stub_server import start_stub_server as start_stub_server
    from je_load_density.utils.stub_server.stub_server import stop_stub_server as stop_stub_server
    from je_load_density.utils.test_record.sqlite_persistence import fetch_run_records as fetch_run_records
    from je_load_density.utils.test_record.sqlite_persistence import list_runs as list_runs
    from je_load_density.utils.test_record.sqlite_persistence import persist_records as persist_records
    from je_load_density.utils.test_record.test_record_class import test_record_instance as test_record_instance
    from je_load_density.utils.throttle.rps_throttle import RpsThrottle as RpsThrottle
    from je_load_density.utils.throttle.rps_throttle import get_throttle as get_throttle
    from je_load_density.utils.throttle.rps_throttle import reset_throttles as reset_throttles
    from je_load_density.wrapper.create_locust_env.create_locust_env import create_env as create_env
    from je_load_density.wrapper.create_locust_env.create_locust_env import prepare_env as prepare_env
    from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy as locust_wrapper_proxy

_MODULE_UTILS_RELIABILITY_ADAPTIVE_RETRY = "je_load_density.utils.reliability.adaptive_retry"
_MODULE_UTILS_RELIABILITY_FAILURE_BUDGET = "je_load_density.utils.reliability.failure_budget"
_MODULE_UTILS_RELIABILITY_NETWORK_CONDITIONER = "je_load_density.utils.reliability.network_conditioner"
_MODULE_UTILS_AUTH_OAUTH2 = "je_load_density.utils.auth.oauth2"
_MODULE_UTILS_THROTTLE_RPS_THROTTLE = "je_load_density.utils.throttle.rps_throttle"
_MODULE_UTILS_LOAD_SHAPES_SHAPES = "je_load_density.utils.load_shapes.shapes"
_MODULE_UTILS_EXECUTOR_ACTION_EXECUTOR = "je_load_density.utils.executor.action_executor"
_MODULE_UTILS_DX_I18N = "je_load_density.utils.dx.i18n"
_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS = "je_load_density.utils.security.graphql_checks"
_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS = "je_load_density.utils.security.smuggling_checks"
_MODULE_UTILS_SECURITY_SSRF_CHECKS = "je_load_density.utils.security.ssrf_checks"
_MODULE_UTILS_RECORDING_CDP_CAPTURE = "je_load_density.utils.recording.cdp_capture"
_MODULE_UTILS_CHAOS_CHAOS_MESH = "je_load_density.utils.chaos.chaos_mesh"
_MODULE_UTILS_SECURITY_OWASP_CHECKS = "je_load_density.utils.security.owasp_checks"
_MODULE_UTILS_SECURITY_JWT_ATTACKS = "je_load_density.utils.security.jwt_attacks"
_MODULE_UTILS_DX_LEAK_DETECTOR = "je_load_density.utils.dx.leak_detector"
_MODULE_UTILS_SECURITY_FUZZ = "je_load_density.utils.security.fuzz"
_MODULE_UTILS_TEST_RECORD_SQLITE_PERSISTENCE = "je_load_density.utils.test_record.sqlite_persistence"
_MODULE_UTILS_DATA_PII_ANONYMIZER = "je_load_density.utils.data.pii_anonymizer"
_MODULE_UTILS_LINTER_ACTION_FORMATTER = "je_load_density.utils.linter.action_formatter"
_MODULE_UTILS_ACTION_GENERATOR_GENERATE = "je_load_density.utils.action_generator.generate"
_MODULE_UTILS_RECORDING_HAR_IMPORTER = "je_load_density.utils.recording.har_importer"
_MODULE_UTILS_SCENARIO_COOKIE_JAR = "je_load_density.utils.scenario.cookie_jar"
_MODULE_UTILS_RECORDING_JMETER_IMPORTER = "je_load_density.utils.recording.jmeter_importer"
_MODULE_UTILS_RECORDING_K6_IMPORTER = "je_load_density.utils.recording.k6_importer"
_MODULE_UTILS_GOVERNANCE_RUN_TAGGING = "je_load_density.utils.governance.run_tagging"
_MODULE_UTILS_RECORDING_OPENAPI_IMPORTER = "je_load_density.utils.recording.openapi_importer"
_MODULE_UTILS_RECORDING_POSTMAN_IMPORTER = "je_load_density.utils.recording.postman_importer"
_MODULE_UTILS_PARAMETERIZATION = "je_load_density.utils.parameterization"
_MODULE_UTILS_DASHBOARD_LIVE_DASHBOARD = "je_load_density.utils.dashboard.live_dashboard"
_MODULE_UTILS_METRICS = "je_load_density.utils.metrics"
_MODULE_UTILS_CHAOS_TOXIPROXY = "je_load_density.utils.chaos.toxiproxy"

_EXPORTS = {
    "AsyncRunHandle": ("je_load_density.engine.asyncio_engine", "AsyncRunHandle"),
    "AdaptiveRetryPolicy": (_MODULE_UTILS_RELIABILITY_ADAPTIVE_RETRY, "AdaptiveRetryPolicy"),
    "AutoTuner": ("je_load_density.utils.ai.auto_tune", "AutoTuner"),
    "CircuitOpenError": (_MODULE_UTILS_RELIABILITY_FAILURE_BUDGET, "CircuitOpenError"),
    "FailureBudget": (_MODULE_UTILS_RELIABILITY_FAILURE_BUDGET, "FailureBudget"),
    "FsmRunner": ("je_load_density.utils.scenario.fsm", "FsmRunner"),
    "NetworkConditioner": (_MODULE_UTILS_RELIABILITY_NETWORK_CONDITIONER, "NetworkConditioner"),
    "OAuth2Client": (_MODULE_UTILS_AUTH_OAUTH2, "OAuth2Client"),
    "ProcessSupervisor": ("je_load_density.utils.reliability.process_supervisor", "ProcessSupervisor"),
    "RpsThrottle": (_MODULE_UTILS_THROTTLE_RPS_THROTTLE, "RpsThrottle"),
    "SequentialTaskSet": ("locust", "SequentialTaskSet"),
    "SoakShape": (_MODULE_UTILS_LOAD_SHAPES_SHAPES, "SoakShape"),
    "SpikeShape": (_MODULE_UTILS_LOAD_SHAPES_SHAPES, "SpikeShape"),
    "StagesShape": (_MODULE_UTILS_LOAD_SHAPES_SHAPES, "StagesShape"),
    "TaskSet": ("locust", "TaskSet"),
    "action_json_schema": ("je_load_density.utils.schema.action_schema", "action_json_schema"),
    "add_command_to_executor": (_MODULE_UTILS_EXECUTOR_ACTION_EXECUTOR, "add_command_to_executor"),
    "append_audit_entry": ("je_load_density.utils.governance.audit_log", "append_audit_entry"),
    "apply_fixture": ("je_load_density.utils.data.db_fixtures", "apply_fixture"),
    "assert_sla": ("je_load_density.utils.sla.sla_gates", "assert_sla"),
    "available_locales": (_MODULE_UTILS_DX_I18N, "available_locales"),
    "build_alias_batching_attack": (_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS, "build_alias_batching_attack"),
    "build_cl_te": (_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS, "build_cl_te"),
    "build_depth_attack": (_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS, "build_depth_attack"),
    "build_gitlab_mr_note": ("je_load_density.utils.notifier.gitlab", "build_gitlab_mr_note"),
    "build_introspection_payload": (_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS, "build_introspection_payload"),
    "build_load_shape": (_MODULE_UTILS_LOAD_SHAPES_SHAPES, "build_load_shape"),
    "build_opsgenie_alert": ("je_load_density.utils.notifier.opsgenie", "build_opsgenie_alert"),
    "build_pagerduty_event": ("je_load_density.utils.notifier.pagerduty", "build_pagerduty_event"),
    "build_root_cause_prompt": ("je_load_density.utils.ai.root_cause", "build_root_cause_prompt"),
    "build_service_map": ("je_load_density.utils.generate_report.generate_service_map", "build_service_map"),
    "build_slack_summary": ("je_load_density.utils.notifier.slack", "build_slack_summary"),
    "build_ssrf_targets": (_MODULE_UTILS_SECURITY_SSRF_CHECKS, "build_ssrf_targets"),
    "build_summary": ("je_load_density.utils.generate_report.generate_summary_report", "build_summary"),
    "build_te_cl": (_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS, "build_te_cl"),
    "build_te_te": (_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS, "build_te_te"),
    "build_teams_summary": ("je_load_density.utils.notifier.teams", "build_teams_summary"),
    "build_user": ("je_load_density.utils.data.factory", "build_user"),
    "build_user_pool": ("je_load_density.utils.data.factory", "build_user_pool"),
    "calibrate_sla": ("je_load_density.utils.ai.auto_baseline", "calibrate_sla"),
    "callback_executor": ("je_load_density.utils.callback.callback_function_executor", "callback_executor"),
    "canary_verdict": ("je_load_density.utils.ci_annotations.canary_analysis", "canary_verdict"),
    "capture_cdp_session": (_MODULE_UTILS_RECORDING_CDP_CAPTURE, "capture_cdp_session"),
    "capture_cdp_to_har": (_MODULE_UTILS_RECORDING_CDP_CAPTURE, "capture_cdp_to_har"),
    "cdp_discover_targets": (_MODULE_UTILS_RECORDING_CDP_CAPTURE, "discover_targets"),
    "chaos_apply_manifest": (_MODULE_UTILS_CHAOS_CHAOS_MESH, "apply_manifest"),
    "chaos_build_network_delay": (_MODULE_UTILS_CHAOS_CHAOS_MESH, "build_network_delay"),
    "chaos_delete_manifest": (_MODULE_UTILS_CHAOS_CHAOS_MESH, "delete_manifest"),
    "check_broken_object_level_auth": (_MODULE_UTILS_SECURITY_OWASP_CHECKS, "check_broken_object_level_auth"),
    "check_excessive_data_exposure": (_MODULE_UTILS_SECURITY_OWASP_CHECKS, "check_excessive_data_exposure"),
    "check_security_headers": (_MODULE_UTILS_SECURITY_OWASP_CHECKS, "check_security_headers"),
    "check_sensitive_token_leak": (_MODULE_UTILS_SECURITY_OWASP_CHECKS, "check_sensitive_token_leak"),
    "classify_error": (_MODULE_UTILS_RELIABILITY_ADAPTIVE_RETRY, "classify_error"),
    "cluster_errors": ("je_load_density.utils.regression.error_clustering", "cluster_errors"),
    "craft_alg_confusion_token": (_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_alg_confusion_token"),
    "craft_alg_none_token": (_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_alg_none_token"),
    "craft_expired_token": (_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_expired_token"),
    "craft_jwt_attack_pack": (_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_attack_pack"),
    "craft_kid_traversal_token": (_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_kid_traversal_token"),
    "create_env": ("je_load_density.wrapper.create_locust_env.create_locust_env", "create_env"),
    "create_project_dir": ("je_load_density.utils.project.create_project_structure", "create_project_dir"),
    "curl_to_task": ("je_load_density.utils.recording.curl_importer", "curl_to_task"),
    "decode_jwt": ("je_load_density.utils.auth.jwt_signer", "decode_jwt"),
    "detect_growing_allocations": (_MODULE_UTILS_DX_LEAK_DETECTOR, "detect_growing_allocations"),
    "diff_runs": ("je_load_density.utils.regression.diff", "diff_runs"),
    "emit_github_annotations": ("je_load_density.utils.ci_annotations.github_actions", "emit_github_annotations"),
    "estimate_run_cost": ("je_load_density.utils.generate_report.generate_cost_report", "estimate_run_cost"),
    "evaluate_sla": ("je_load_density.utils.sla.sla_gates", "evaluate_sla"),
    "execute_action": (_MODULE_UTILS_EXECUTOR_ACTION_EXECUTOR, "execute_action"),
    "execute_files": (_MODULE_UTILS_EXECUTOR_ACTION_EXECUTOR, "execute_files"),
    "executor": (_MODULE_UTILS_EXECUTOR_ACTION_EXECUTOR, "executor"),
    "expand_task_fuzz": (_MODULE_UTILS_SECURITY_FUZZ, "expand_task_fuzz"),
    "export_schema": ("je_load_density.utils.schema.action_schema", "export_schema"),
    "extract_field": ("je_load_density.utils.graphql.graphql_task", "extract_field"),
    "fetch_client_credentials_token": (_MODULE_UTILS_AUTH_OAUTH2, "fetch_client_credentials_token"),
    "fetch_password_token": (_MODULE_UTILS_AUTH_OAUTH2, "fetch_password_token"),
    "fetch_run_records": (_MODULE_UTILS_TEST_RECORD_SQLITE_PERSISTENCE, "fetch_run_records"),
    "find_breaking_point": ("je_load_density.utils.ai.smart_shape", "find_breaking_point"),
    "find_metadata_leak": (_MODULE_UTILS_SECURITY_SSRF_CHECKS, "find_metadata_leak"),
    "find_pii": (_MODULE_UTILS_DATA_PII_ANONYMIZER, "find_pii"),
    "format_action_document": (_MODULE_UTILS_LINTER_ACTION_FORMATTER, "format_action_document"),
    "format_action_file": (_MODULE_UTILS_LINTER_ACTION_FORMATTER, "format_action_file"),
    "format_action_string": (_MODULE_UTILS_LINTER_ACTION_FORMATTER, "format_action_string"),
    "format_github_annotation": ("je_load_density.utils.ci_annotations.github_actions", "format_github_annotation"),
    "fuzz_query_string": (_MODULE_UTILS_SECURITY_FUZZ, "fuzz_query_string"),
    "generate_allure_report": (
        "je_load_density.utils.generate_report.generate_allure_report",
        "generate_allure_report",
    ),
    "generate_chart_report": ("je_load_density.utils.generate_report.generate_chart_report", "generate_chart_report"),
    "generate_cost_report": ("je_load_density.utils.generate_report.generate_cost_report", "generate_cost_report"),
    "generate_csv_report": ("je_load_density.utils.generate_report.generate_csv_report", "generate_csv_report"),
    "generate_cyclonedx_report": (
        "je_load_density.utils.generate_report.generate_cyclonedx_report",
        "generate_cyclonedx_report",
    ),
    "generate_excel_report": ("je_load_density.utils.generate_report.generate_excel_report", "generate_excel_report"),
    "generate_from_curls": (_MODULE_UTILS_ACTION_GENERATOR_GENERATE, "generate_from_curls"),
    "generate_from_openapi": (_MODULE_UTILS_ACTION_GENERATOR_GENERATE, "generate_from_openapi"),
    "generate_histogram_report": (
        "je_load_density.utils.generate_report.generate_histogram_report",
        "generate_histogram_report",
    ),
    "generate_html": ("je_load_density.utils.generate_report.generate_html_report", "generate_html"),
    "generate_html_report": ("je_load_density.utils.generate_report.generate_html_report", "generate_html_report"),
    "generate_json": ("je_load_density.utils.generate_report.generate_json_report", "generate_json"),
    "generate_json_report": ("je_load_density.utils.generate_report.generate_json_report", "generate_json_report"),
    "generate_junit_report": ("je_load_density.utils.generate_report.generate_junit_report", "generate_junit_report"),
    "generate_pdf_report": ("je_load_density.utils.generate_report.generate_pdf_report", "generate_pdf_report"),
    "generate_sarif_report": ("je_load_density.utils.generate_report.generate_sarif_report", "generate_sarif_report"),
    "generate_service_map": ("je_load_density.utils.generate_report.generate_service_map", "generate_service_map"),
    "generate_summary_report": (
        "je_load_density.utils.generate_report.generate_summary_report",
        "generate_summary_report",
    ),
    "generate_xml": ("je_load_density.utils.generate_report.generate_xml_report", "generate_xml"),
    "generate_xml_report": ("je_load_density.utils.generate_report.generate_xml_report", "generate_xml_report"),
    "get_current_locale": (_MODULE_UTILS_DX_I18N, "get_current_locale"),
    "get_dir_files_as_list": ("je_load_density.utils.file_process.get_dir_file_list", "get_dir_files_as_list"),
    "get_throttle": (_MODULE_UTILS_THROTTLE_RPS_THROTTLE, "get_throttle"),
    "graphql_attack_pack": (_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS, "graphql_attack_pack"),
    "graphql_to_http_task": ("je_load_density.utils.graphql.graphql_task", "graphql_to_http_task"),
    "har_to_action_json": (_MODULE_UTILS_RECORDING_HAR_IMPORTER, "har_to_action_json"),
    "har_to_tasks": (_MODULE_UTILS_RECORDING_HAR_IMPORTER, "har_to_tasks"),
    "index_catalog": ("je_load_density.utils.governance.test_catalog", "index_catalog"),
    "install_failure_budget": (_MODULE_UTILS_RELIABILITY_FAILURE_BUDGET, "install_failure_budget"),
    "install_network_conditioner": (
        _MODULE_UTILS_RELIABILITY_NETWORK_CONDITIONER,
        "install_network_conditioner",
    ),
    "invoke_lambda_workers": ("je_load_density.cloud.aws_lambda", "invoke_lambda_workers"),
    "issue_share_link": ("je_load_density.utils.governance.share_link", "issue_share_link"),
    "jar_for_user": (_MODULE_UTILS_SCENARIO_COOKIE_JAR, "jar_for_user"),
    "jmeter_to_action_json": (_MODULE_UTILS_RECORDING_JMETER_IMPORTER, "jmeter_to_action_json"),
    "jmeter_to_tasks": (_MODULE_UTILS_RECORDING_JMETER_IMPORTER, "jmeter_to_tasks"),
    "k6_script_to_action_json": (_MODULE_UTILS_RECORDING_K6_IMPORTER, "k6_script_to_action_json"),
    "k6_script_to_tasks": (_MODULE_UTILS_RECORDING_K6_IMPORTER, "k6_script_to_tasks"),
    "lambda_worker_handler": ("je_load_density.cloud.aws_lambda", "lambda_worker_handler"),
    "launch_aci_workers": ("je_load_density.cloud.azure_aci", "launch_aci_workers"),
    "launch_fargate_workers": ("je_load_density.cloud.aws_fargate", "launch_fargate_workers"),
    "lint_action": ("je_load_density.utils.linter.action_linter", "lint_action"),
    "lint_action_file": ("je_load_density.utils.linter.action_linter", "lint_action_file"),
    "list_runs": (_MODULE_UTILS_TEST_RECORD_SQLITE_PERSISTENCE, "list_runs"),
    "list_tags": (_MODULE_UTILS_GOVERNANCE_RUN_TAGGING, "list_tags"),
    "load_har": (_MODULE_UTILS_RECORDING_HAR_IMPORTER, "load_har"),
    "load_jmeter_jmx": (_MODULE_UTILS_RECORDING_JMETER_IMPORTER, "load_jmeter_jmx"),
    "load_k6_script": (_MODULE_UTILS_RECORDING_K6_IMPORTER, "load_k6_script"),
    "load_openapi": (_MODULE_UTILS_RECORDING_OPENAPI_IMPORTER, "load_openapi"),
    "load_postman_collection": (_MODULE_UTILS_RECORDING_POSTMAN_IMPORTER, "load_postman_collection"),
    "locust_wrapper_proxy": ("je_load_density.wrapper.proxy.proxy_user", "locust_wrapper_proxy"),
    "memory_snapshot": ("je_load_density.utils.dx.profiler", "memory_snapshot"),
    "merge_actions": (_MODULE_UTILS_ACTION_GENERATOR_GENERATE, "merge_actions"),
    "mutate_json": (_MODULE_UTILS_SECURITY_FUZZ, "mutate_json"),
    "mutate_string": (_MODULE_UTILS_SECURITY_FUZZ, "mutate_string"),
    "openapi_to_action_json": (_MODULE_UTILS_RECORDING_OPENAPI_IMPORTER, "openapi_to_action_json"),
    "openapi_to_tasks": (_MODULE_UTILS_RECORDING_OPENAPI_IMPORTER, "openapi_to_tasks"),
    "parameter_resolver": (_MODULE_UTILS_PARAMETERIZATION, "parameter_resolver"),
    "persist_records": (_MODULE_UTILS_TEST_RECORD_SQLITE_PERSISTENCE, "persist_records"),
    "pii_scrub": (_MODULE_UTILS_DATA_PII_ANONYMIZER, "scrub"),
    "pii_scrub_string": (_MODULE_UTILS_DATA_PII_ANONYMIZER, "scrub_string"),
    "post_gitlab_mr_summary": ("je_load_density.utils.notifier.gitlab", "post_gitlab_mr_summary"),
    "post_opsgenie_alert": ("je_load_density.utils.notifier.opsgenie", "post_opsgenie_alert"),
    "post_pagerduty_event": ("je_load_density.utils.notifier.pagerduty", "post_pagerduty_event"),
    "post_slack_summary": ("je_load_density.utils.notifier.slack", "post_slack_summary"),
    "post_teams_summary": ("je_load_density.utils.notifier.teams", "post_teams_summary"),
    "postman_to_action_json": (_MODULE_UTILS_RECORDING_POSTMAN_IMPORTER, "postman_to_action_json"),
    "postman_to_tasks": (_MODULE_UTILS_RECORDING_POSTMAN_IMPORTER, "postman_to_tasks"),
    "prepare_env": ("je_load_density.wrapper.create_locust_env.create_locust_env", "prepare_env"),
    "probe_rate_limit": ("je_load_density.utils.security.rate_limit_probe", "probe_rate_limit"),
    "profile_call": ("je_load_density.utils.dx.profiler", "profile_call"),
    "read_action_json": ("je_load_density.utils.json.json_file.json_file", "read_action_json"),
    "read_action_toml": ("je_load_density.utils.json.json_file.toml_file", "read_action_toml"),
    "read_action_yaml": ("je_load_density.utils.json.json_file.yaml_file", "read_action_yaml"),
    "read_audit_log": ("je_load_density.utils.governance.audit_log", "read_audit_log"),
    "refresh_token": (_MODULE_UTILS_AUTH_OAUTH2, "refresh_token"),
    "register_csv_source": (_MODULE_UTILS_PARAMETERIZATION, "register_csv_source"),
    "register_csv_sources": (_MODULE_UTILS_PARAMETERIZATION, "register_csv_sources"),
    "register_db_source": (_MODULE_UTILS_PARAMETERIZATION, "register_db_source"),
    "register_db_sources": (_MODULE_UTILS_PARAMETERIZATION, "register_db_sources"),
    "register_variable": (_MODULE_UTILS_PARAMETERIZATION, "register_variable"),
    "get_resolver": (_MODULE_UTILS_PARAMETERIZATION, "get_resolver"),
    "use_resolver": (_MODULE_UTILS_PARAMETERIZATION, "use_resolver"),
    "register_session_variable": (_MODULE_UTILS_PARAMETERIZATION, "register_session_variable"),
    "register_variables": (_MODULE_UTILS_PARAMETERIZATION, "register_variables"),
    "render_prompt_text": ("je_load_density.utils.ai.root_cause", "render_prompt_text"),
    "render_ssrf_tasks": (_MODULE_UTILS_SECURITY_SSRF_CHECKS, "render_ssrf_tasks"),
    "request_hook": ("je_load_density.wrapper.event.request_hook", "request_hook"),
    "reset_all_jars": (_MODULE_UTILS_SCENARIO_COOKIE_JAR, "reset_all_jars"),
    "reset_throttles": (_MODULE_UTILS_THROTTLE_RPS_THROTTLE, "reset_throttles"),
    "reset_user_jar": (_MODULE_UTILS_SCENARIO_COOKIE_JAR, "reset_user_jar"),
    "resolve": (_MODULE_UTILS_PARAMETERIZATION, "resolve"),
    "run_async_load": ("je_load_density.engine.asyncio_engine", "run_async_load"),
    "run_cloud_run_job": ("je_load_density.cloud.gcp_cloud_run", "run_cloud_run_job"),
    "run_owasp_checks": (_MODULE_UTILS_SECURITY_OWASP_CHECKS, "run_owasp_checks"),
    "run_teardown": ("je_load_density.utils.data.db_fixtures", "run_teardown"),
    "run_with_retry": (_MODULE_UTILS_RELIABILITY_ADAPTIVE_RETRY, "run_with_retry"),
    "search_catalog": ("je_load_density.utils.governance.test_catalog", "search_catalog"),
    "search_runs_by_tag": (_MODULE_UTILS_GOVERNANCE_RUN_TAGGING, "search_runs_by_tag"),
    "sign_aws_request": ("je_load_density.utils.auth.aws_sigv4", "sign_aws_request"),
    "sign_jwt": ("je_load_density.utils.auth.jwt_signer", "sign_jwt"),
    "smuggling_attack_pack": (_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS, "smuggling_attack_pack"),
    "snapshot_metrics": (_MODULE_UTILS_DASHBOARD_LIVE_DASHBOARD, "snapshot_metrics"),
    "start_dashboard": (_MODULE_UTILS_DASHBOARD_LIVE_DASHBOARD, "start_dashboard"),
    "start_datadog_apm_exporter": ("je_load_density.utils.metrics.datadog_apm_exporter", "start_datadog_apm_exporter"),
    "start_influxdb_sink": (_MODULE_UTILS_METRICS, "start_influxdb_sink"),
    "start_leak_detector": (_MODULE_UTILS_DX_LEAK_DETECTOR, "start_leak_detector"),
    "start_load_density_socket_server": (
        "je_load_density.utils.socket_server.load_density_socket_server",
        "start_load_density_socket_server",
    ),
    "start_opentelemetry_exporter": (_MODULE_UTILS_METRICS, "start_opentelemetry_exporter"),
    "start_opentelemetry_tracing_exporter": (
        "je_load_density.utils.metrics.opentelemetry_tracing_exporter",
        "start_opentelemetry_tracing_exporter",
    ),
    "start_prometheus_exporter": (_MODULE_UTILS_METRICS, "start_prometheus_exporter"),
    "start_repl": ("je_load_density.utils.dx.repl", "start_repl"),
    "start_statsd_sink": ("je_load_density.utils.metrics.statsd_sink", "start_statsd_sink"),
    "start_stub_server": ("je_load_density.utils.stub_server.stub_server", "start_stub_server"),
    "start_test": ("je_load_density.engine.entrypoints", "start_test"),
    "stop_dashboard": (_MODULE_UTILS_DASHBOARD_LIVE_DASHBOARD, "stop_dashboard"),
    "stop_datadog_apm_exporter": ("je_load_density.utils.metrics.datadog_apm_exporter", "stop_datadog_apm_exporter"),
    "stop_influxdb_sink": (_MODULE_UTILS_METRICS, "stop_influxdb_sink"),
    "stop_leak_detector": (_MODULE_UTILS_DX_LEAK_DETECTOR, "stop_leak_detector"),
    "stop_opentelemetry_exporter": (_MODULE_UTILS_METRICS, "stop_opentelemetry_exporter"),
    "stop_opentelemetry_tracing_exporter": (
        "je_load_density.utils.metrics.opentelemetry_tracing_exporter",
        "stop_opentelemetry_tracing_exporter",
    ),
    "stop_prometheus_exporter": (_MODULE_UTILS_METRICS, "stop_prometheus_exporter"),
    "stop_statsd_sink": ("je_load_density.utils.metrics.statsd_sink", "stop_statsd_sink"),
    "stop_stub_server": ("je_load_density.utils.stub_server.stub_server", "stop_stub_server"),
    "summarise_records": ("je_load_density.utils.regression.diff", "summarise_records"),
    "tag_run": (_MODULE_UTILS_GOVERNANCE_RUN_TAGGING, "tag_run"),
    "task": ("locust", "task"),
    "test_record_instance": ("je_load_density.utils.test_record.test_record_class", "test_record_instance"),
    "toxiproxy_add_toxic": (_MODULE_UTILS_CHAOS_TOXIPROXY, "add_toxic"),
    "toxiproxy_create_proxy": (_MODULE_UTILS_CHAOS_TOXIPROXY, "create_proxy"),
    "toxiproxy_install_bandwidth": (_MODULE_UTILS_CHAOS_TOXIPROXY, "install_bandwidth"),
    "toxiproxy_install_latency": (_MODULE_UTILS_CHAOS_TOXIPROXY, "install_latency"),
    "toxiproxy_list_proxies": (_MODULE_UTILS_CHAOS_TOXIPROXY, "list_proxies"),
    "toxiproxy_remove_proxies": (_MODULE_UTILS_CHAOS_TOXIPROXY, "remove_proxies"),
    "toxiproxy_remove_toxic": (_MODULE_UTILS_CHAOS_TOXIPROXY, "remove_toxic"),
    "toxiproxy_reset_all": (_MODULE_UTILS_CHAOS_TOXIPROXY, "reset_all"),
    "translate": (_MODULE_UTILS_DX_I18N, "t"),
    "trend_runs": ("je_load_density.utils.regression.multi_run_trend", "trend_runs"),
    "uninstall_failure_budget": (_MODULE_UTILS_RELIABILITY_FAILURE_BUDGET, "uninstall_failure_budget"),
    "uninstall_network_conditioner": (
        _MODULE_UTILS_RELIABILITY_NETWORK_CONDITIONER,
        "uninstall_network_conditioner",
    ),
    "verify_share_link": ("je_load_density.utils.governance.share_link", "verify_share_link"),
    "with_watchdog": ("je_load_density.utils.reliability.process_supervisor", "with_watchdog"),
    "write_action_toml": ("je_load_density.utils.json.json_file.toml_file", "write_action_toml"),
    "write_action_yaml": ("je_load_density.utils.json.json_file.yaml_file", "write_action_yaml"),
}

__all__ = [
    "AsyncRunHandle",
    "create_env",
    "start_test",
    "locust_wrapper_proxy",
    "prepare_env",
    "test_record_instance",
    "execute_action",
    "execute_files",
    "executor",
    "add_command_to_executor",
    "get_dir_files_as_list",
    "generate_html",
    "generate_html_report",
    "generate_json",
    "generate_json_report",
    "generate_xml",
    "generate_xml_report",
    "generate_csv_report",
    "generate_junit_report",
    "generate_summary_report",
    "generate_chart_report",
    "build_summary",
    "read_action_json",
    "start_load_density_socket_server",
    "SequentialTaskSet",
    "task",
    "TaskSet",
    "callback_executor",
    "create_project_dir",
    "parameter_resolver",
    "resolve",
    "register_variable",
    "get_resolver",
    "use_resolver",
    "register_session_variable",
    "register_variables",
    "register_csv_source",
    "register_csv_sources",
    "register_db_source",
    "register_db_sources",
    "har_to_action_json",
    "har_to_tasks",
    "load_har",
    "postman_to_action_json",
    "postman_to_tasks",
    "load_postman_collection",
    "openapi_to_action_json",
    "openapi_to_tasks",
    "load_openapi",
    "curl_to_task",
    "persist_records",
    "list_runs",
    "fetch_run_records",
    "start_prometheus_exporter",
    "stop_prometheus_exporter",
    "start_influxdb_sink",
    "stop_influxdb_sink",
    "start_opentelemetry_exporter",
    "stop_opentelemetry_exporter",
    "lint_action",
    "lint_action_file",
    "action_json_schema",
    "export_schema",
    "emit_github_annotations",
    "format_github_annotation",
    "evaluate_sla",
    "assert_sla",
    "diff_runs",
    "summarise_records",
    "SoakShape",
    "SpikeShape",
    "StagesShape",
    "build_load_shape",
    "graphql_to_http_task",
    "extract_field",
    "RpsThrottle",
    "get_throttle",
    "reset_throttles",
    "AdaptiveRetryPolicy",
    "classify_error",
    "run_with_retry",
    "FailureBudget",
    "CircuitOpenError",
    "install_failure_budget",
    "uninstall_failure_budget",
    "NetworkConditioner",
    "install_network_conditioner",
    "uninstall_network_conditioner",
    "ProcessSupervisor",
    "with_watchdog",
    "start_dashboard",
    "stop_dashboard",
    "snapshot_metrics",
    "post_slack_summary",
    "build_slack_summary",
    "post_teams_summary",
    "build_teams_summary",
    "start_statsd_sink",
    "stop_statsd_sink",
    "jmeter_to_action_json",
    "jmeter_to_tasks",
    "load_jmeter_jmx",
    "k6_script_to_action_json",
    "k6_script_to_tasks",
    "load_k6_script",
    "OAuth2Client",
    "fetch_client_credentials_token",
    "fetch_password_token",
    "refresh_token",
    "sign_jwt",
    "decode_jwt",
    "sign_aws_request",
    # New report formats
    "generate_histogram_report",
    "generate_pdf_report",
    "generate_allure_report",
    # YAML / TOML loaders
    "read_action_yaml",
    "write_action_yaml",
    "read_action_toml",
    "write_action_toml",
    # Tracing & APM exporters
    "start_opentelemetry_tracing_exporter",
    "stop_opentelemetry_tracing_exporter",
    "start_datadog_apm_exporter",
    "stop_datadog_apm_exporter",
    # Notifier
    "post_pagerduty_event",
    "build_pagerduty_event",
    "post_opsgenie_alert",
    "build_opsgenie_alert",
    "post_gitlab_mr_summary",
    "build_gitlab_mr_note",
    # Trend & error clustering
    "trend_runs",
    "cluster_errors",
    # DX
    "format_action_document",
    "format_action_file",
    "format_action_string",
    "generate_from_openapi",
    "generate_from_curls",
    "merge_actions",
    # Scenario
    "FsmRunner",
    "jar_for_user",
    "reset_user_jar",
    "reset_all_jars",
    # Stub server
    "start_stub_server",
    "stop_stub_server",
    # Security
    "mutate_string",
    "mutate_json",
    "fuzz_query_string",
    "expand_task_fuzz",
    "run_owasp_checks",
    "check_broken_object_level_auth",
    "check_excessive_data_exposure",
    "check_security_headers",
    "check_sensitive_token_leak",
    # Chaos
    "toxiproxy_create_proxy",
    "toxiproxy_list_proxies",
    "toxiproxy_add_toxic",
    "toxiproxy_remove_toxic",
    "toxiproxy_install_latency",
    "toxiproxy_install_bandwidth",
    "toxiproxy_reset_all",
    "toxiproxy_remove_proxies",
    "chaos_apply_manifest",
    "chaos_delete_manifest",
    "chaos_build_network_delay",
    # Asyncio engine
    "run_async_load",
    # AI
    "AutoTuner",
    "build_root_cause_prompt",
    "render_prompt_text",
    "find_breaking_point",
    "calibrate_sla",
    # Cloud workers
    "invoke_lambda_workers",
    "lambda_worker_handler",
    "launch_fargate_workers",
    "launch_aci_workers",
    "run_cloud_run_job",
    # CI / canary
    "canary_verdict",
    # Data / state
    "apply_fixture",
    "run_teardown",
    "build_user",
    "build_user_pool",
    "pii_scrub",
    "pii_scrub_string",
    "find_pii",
    # DX
    "start_repl",
    "profile_call",
    "memory_snapshot",
    "start_leak_detector",
    "stop_leak_detector",
    "detect_growing_allocations",
    "translate",
    "available_locales",
    "get_current_locale",
    # Governance
    "append_audit_entry",
    "read_audit_log",
    "tag_run",
    "list_tags",
    "search_runs_by_tag",
    "issue_share_link",
    "verify_share_link",
    "index_catalog",
    "search_catalog",
    # Reports (additional)
    "generate_excel_report",
    "generate_sarif_report",
    "generate_cyclonedx_report",
    "generate_service_map",
    "build_service_map",
    "generate_cost_report",
    "estimate_run_cost",
    # Recording (additional)
    "cdp_discover_targets",
    "capture_cdp_session",
    "capture_cdp_to_har",
    # Security: extended
    "craft_alg_none_token",
    "craft_alg_confusion_token",
    "craft_expired_token",
    "craft_kid_traversal_token",
    "craft_jwt_attack_pack",
    "build_introspection_payload",
    "build_depth_attack",
    "build_alias_batching_attack",
    "graphql_attack_pack",
    "build_ssrf_targets",
    "render_ssrf_tasks",
    "find_metadata_leak",
    "build_cl_te",
    "build_te_cl",
    "build_te_te",
    "smuggling_attack_pack",
    "probe_rate_limit",
]


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = target
    # Security audit: Only targets from the fixed _EXPORTS map reach this import; unknown names raise before import.
    # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
    value = getattr(importlib.import_module(module), attribute)
    if module == "locust":
        importlib.import_module("je_load_density.wrapper.event.request_hook")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))
