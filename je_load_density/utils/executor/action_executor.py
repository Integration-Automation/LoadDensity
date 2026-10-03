from typing import Any

from je_action_core import (
    SAFE_BUILTINS,
    ActionExecutor,
    ActionListRules,
    CommandPolicy,
    CommandRegistry,
    ExecutorSettings,
    LegacyActionParser,
    PrintReporter,
    safe_builtin_commands,
)

from je_load_density.utils.exception.exception_tags import (
    add_command_exception_tag,
    executor_data_error,
    executor_list_error,
)
from je_load_density.utils.exception.exceptions import LoadDensityTestExecuteException
from je_load_density.utils.package_manager.package_manager_class import package_manager
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_source,
    register_csv_sources,
    register_db_source,
    register_db_sources,
    register_variable,
    register_variables,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance


def _lazy_command(module: str, attribute: str):
    """Keep registry entries as functions while deferring their implementation import."""

    def command(*args, **kwargs):
        from importlib import import_module

        function = getattr(import_module(module), attribute)
        return function(*args, **kwargs)

    command.__name__ = attribute
    return command


_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS = "je_load_density.utils.security.graphql_checks"
_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS = "je_load_density.utils.security.smuggling_checks"
_MODULE_UTILS_SECURITY_SSRF_CHECKS = "je_load_density.utils.security.ssrf_checks"
_MODULE_UTILS_RECORDING_CDP_CAPTURE = "je_load_density.utils.recording.cdp_capture"
_MODULE_UTILS_CHAOS_CHAOS_MESH = "je_load_density.utils.chaos.chaos_mesh"
_MODULE_UTILS_SECURITY_JWT_ATTACKS = "je_load_density.utils.security.jwt_attacks"
_MODULE_UTILS_SECURITY_FUZZ = "je_load_density.utils.security.fuzz"
_MODULE_UTILS_TEST_RECORD_SQLITE_PERSISTENCE = "je_load_density.utils.test_record.sqlite_persistence"
_MODULE_UTILS_LINTER_ACTION_FORMATTER = "je_load_density.utils.linter.action_formatter"
_MODULE_UTILS_RECORDING_HAR_IMPORTER = "je_load_density.utils.recording.har_importer"
_MODULE_UTILS_RECORDING_JMETER_IMPORTER = "je_load_density.utils.recording.jmeter_importer"
_MODULE_UTILS_RECORDING_K6_IMPORTER = "je_load_density.utils.recording.k6_importer"
_MODULE_UTILS_GOVERNANCE_RUN_TAGGING = "je_load_density.utils.governance.run_tagging"
_MODULE_UTILS_RECORDING_OPENAPI_IMPORTER = "je_load_density.utils.recording.openapi_importer"
_MODULE_UTILS_RECORDING_POSTMAN_IMPORTER = "je_load_density.utils.recording.postman_importer"
_MODULE_UTILS_CHAOS_TOXIPROXY = "je_load_density.utils.chaos.toxiproxy"

append_audit_entry = _lazy_command("je_load_density.utils.governance.audit_log", "append_audit_entry")
apply_db_fixture = _lazy_command("je_load_density.utils.data.db_fixtures", "apply_fixture")
assert_sla = _lazy_command("je_load_density.utils.sla.sla_gates", "assert_sla")
build_alias_batching_attack = _lazy_command(_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS, "build_alias_batching_attack")
build_cl_te = _lazy_command(_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS, "build_cl_te")
build_depth_attack = _lazy_command(_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS, "build_depth_attack")
build_introspection_payload = _lazy_command(_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS, "build_introspection_payload")
build_root_cause_prompt = _lazy_command("je_load_density.utils.ai.root_cause", "build_root_cause_prompt")
build_ssrf_targets = _lazy_command(_MODULE_UTILS_SECURITY_SSRF_CHECKS, "build_ssrf_targets")
build_summary = _lazy_command("je_load_density.utils.generate_report.generate_summary_report", "build_summary")
build_te_cl = _lazy_command(_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS, "build_te_cl")
build_te_te = _lazy_command(_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS, "build_te_te")
build_user = _lazy_command("je_load_density.utils.data.factory", "build_user")
build_user_pool = _lazy_command("je_load_density.utils.data.factory", "build_user_pool")
calibrate_sla = _lazy_command("je_load_density.utils.ai.auto_baseline", "calibrate_sla")
canary_verdict = _lazy_command("je_load_density.utils.ci_annotations.canary_analysis", "canary_verdict")
capture_cdp_session = _lazy_command(_MODULE_UTILS_RECORDING_CDP_CAPTURE, "capture_cdp_session")
capture_cdp_to_har = _lazy_command(_MODULE_UTILS_RECORDING_CDP_CAPTURE, "capture_cdp_to_har")
cdp_discover_targets = _lazy_command(_MODULE_UTILS_RECORDING_CDP_CAPTURE, "discover_targets")
chaos_apply_manifest = _lazy_command(_MODULE_UTILS_CHAOS_CHAOS_MESH, "apply_manifest")
chaos_delete_manifest = _lazy_command(_MODULE_UTILS_CHAOS_CHAOS_MESH, "delete_manifest")
chaos_network_delay = _lazy_command(_MODULE_UTILS_CHAOS_CHAOS_MESH, "build_network_delay")
cluster_errors = _lazy_command("je_load_density.utils.regression.error_clustering", "cluster_errors")
craft_alg_confusion_token = _lazy_command(_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_alg_confusion_token")
craft_alg_none_token = _lazy_command(_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_alg_none_token")
craft_expired_token = _lazy_command(_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_expired_token")
craft_jwt_attack_pack = _lazy_command(_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_attack_pack")
craft_kid_traversal_token = _lazy_command(_MODULE_UTILS_SECURITY_JWT_ATTACKS, "craft_kid_traversal_token")
curl_to_task = _lazy_command("je_load_density.utils.recording.curl_importer", "curl_to_task")
diff_runs = _lazy_command("je_load_density.utils.regression.diff", "diff_runs")
emit_github_annotations = _lazy_command(
    "je_load_density.utils.ci_annotations.github_actions", "emit_github_annotations"
)
evaluate_sla = _lazy_command("je_load_density.utils.sla.sla_gates", "evaluate_sla")
expand_task_fuzz = _lazy_command(_MODULE_UTILS_SECURITY_FUZZ, "expand_task_fuzz")
export_schema = _lazy_command("je_load_density.utils.schema.action_schema", "export_schema")
fetch_run_records = _lazy_command(_MODULE_UTILS_TEST_RECORD_SQLITE_PERSISTENCE, "fetch_run_records")
find_breaking_point = _lazy_command("je_load_density.utils.ai.smart_shape", "find_breaking_point")
find_metadata_leak = _lazy_command(_MODULE_UTILS_SECURITY_SSRF_CHECKS, "find_metadata_leak")
format_action_document = _lazy_command(_MODULE_UTILS_LINTER_ACTION_FORMATTER, "format_action_document")
format_action_file = _lazy_command(_MODULE_UTILS_LINTER_ACTION_FORMATTER, "format_action_file")
format_action_string = _lazy_command(_MODULE_UTILS_LINTER_ACTION_FORMATTER, "format_action_string")
generate_allure_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_allure_report", "generate_allure_report"
)
generate_chart_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_chart_report", "generate_chart_report"
)
generate_cost_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_cost_report", "generate_cost_report"
)
generate_csv_report = _lazy_command("je_load_density.utils.generate_report.generate_csv_report", "generate_csv_report")
generate_cyclonedx_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_cyclonedx_report", "generate_cyclonedx_report"
)
generate_excel_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_excel_report", "generate_excel_report"
)
generate_from_curls = _lazy_command("je_load_density.utils.action_generator.generate", "generate_from_curls")
generate_from_openapi = _lazy_command("je_load_density.utils.action_generator.generate", "generate_from_openapi")
generate_histogram_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_histogram_report", "generate_histogram_report"
)
generate_html = _lazy_command("je_load_density.utils.generate_report.generate_html_report", "generate_html")
generate_html_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_html_report", "generate_html_report"
)
generate_json = _lazy_command("je_load_density.utils.generate_report.generate_json_report", "generate_json")
generate_json_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_json_report", "generate_json_report"
)
generate_junit_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_junit_report", "generate_junit_report"
)
generate_pdf_report = _lazy_command("je_load_density.utils.generate_report.generate_pdf_report", "generate_pdf_report")
generate_sarif_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_sarif_report", "generate_sarif_report"
)
generate_service_map = _lazy_command(
    "je_load_density.utils.generate_report.generate_service_map", "generate_service_map"
)
generate_summary_report = _lazy_command(
    "je_load_density.utils.generate_report.generate_summary_report", "generate_summary_report"
)
generate_xml = _lazy_command("je_load_density.utils.generate_report.generate_xml_report", "generate_xml")
generate_xml_report = _lazy_command("je_load_density.utils.generate_report.generate_xml_report", "generate_xml_report")
graphql_attack_pack = _lazy_command(_MODULE_UTILS_SECURITY_GRAPHQL_CHECKS, "graphql_attack_pack")
har_to_action_json = _lazy_command(_MODULE_UTILS_RECORDING_HAR_IMPORTER, "har_to_action_json")
har_to_tasks = _lazy_command(_MODULE_UTILS_RECORDING_HAR_IMPORTER, "har_to_tasks")
index_catalog = _lazy_command("je_load_density.utils.governance.test_catalog", "index_catalog")
install_failure_budget = _lazy_command("je_load_density.utils.reliability.failure_budget", "install_failure_budget")
install_network_conditioner = _lazy_command(
    "je_load_density.utils.reliability.network_conditioner", "install_network_conditioner"
)
issue_share_link = _lazy_command("je_load_density.utils.governance.share_link", "issue_share_link")
jmeter_to_action_json = _lazy_command(_MODULE_UTILS_RECORDING_JMETER_IMPORTER, "jmeter_to_action_json")
jmeter_to_tasks = _lazy_command(_MODULE_UTILS_RECORDING_JMETER_IMPORTER, "jmeter_to_tasks")
k6_script_to_action_json = _lazy_command(_MODULE_UTILS_RECORDING_K6_IMPORTER, "k6_script_to_action_json")
k6_script_to_tasks = _lazy_command(_MODULE_UTILS_RECORDING_K6_IMPORTER, "k6_script_to_tasks")
lint_action = _lazy_command("je_load_density.utils.linter.action_linter", "lint_action")
lint_action_file = _lazy_command("je_load_density.utils.linter.action_linter", "lint_action_file")
list_runs = _lazy_command(_MODULE_UTILS_TEST_RECORD_SQLITE_PERSISTENCE, "list_runs")
list_tags = _lazy_command(_MODULE_UTILS_GOVERNANCE_RUN_TAGGING, "list_tags")
load_har = _lazy_command(_MODULE_UTILS_RECORDING_HAR_IMPORTER, "load_har")
load_jmeter_jmx = _lazy_command(_MODULE_UTILS_RECORDING_JMETER_IMPORTER, "load_jmeter_jmx")
load_k6_script = _lazy_command(_MODULE_UTILS_RECORDING_K6_IMPORTER, "load_k6_script")
load_openapi = _lazy_command(_MODULE_UTILS_RECORDING_OPENAPI_IMPORTER, "load_openapi")
load_postman_collection = _lazy_command(_MODULE_UTILS_RECORDING_POSTMAN_IMPORTER, "load_postman_collection")
mutate_json = _lazy_command(_MODULE_UTILS_SECURITY_FUZZ, "mutate_json")
mutate_string = _lazy_command(_MODULE_UTILS_SECURITY_FUZZ, "mutate_string")
openapi_to_action_json = _lazy_command(_MODULE_UTILS_RECORDING_OPENAPI_IMPORTER, "openapi_to_action_json")
openapi_to_tasks = _lazy_command(_MODULE_UTILS_RECORDING_OPENAPI_IMPORTER, "openapi_to_tasks")
persist_records = _lazy_command(_MODULE_UTILS_TEST_RECORD_SQLITE_PERSISTENCE, "persist_records")
pii_scrub = _lazy_command("je_load_density.utils.data.pii_anonymizer", "scrub")
pii_scrub_string = _lazy_command("je_load_density.utils.data.pii_anonymizer", "scrub_string")
post_gitlab_mr_summary = _lazy_command("je_load_density.utils.notifier.gitlab", "post_gitlab_mr_summary")
post_opsgenie_alert = _lazy_command("je_load_density.utils.notifier.opsgenie", "post_opsgenie_alert")
post_pagerduty_event = _lazy_command("je_load_density.utils.notifier.pagerduty", "post_pagerduty_event")
post_slack_summary = _lazy_command("je_load_density.utils.notifier.slack", "post_slack_summary")
post_teams_summary = _lazy_command("je_load_density.utils.notifier.teams", "post_teams_summary")
postman_to_action_json = _lazy_command(_MODULE_UTILS_RECORDING_POSTMAN_IMPORTER, "postman_to_action_json")
postman_to_tasks = _lazy_command(_MODULE_UTILS_RECORDING_POSTMAN_IMPORTER, "postman_to_tasks")
probe_rate_limit = _lazy_command("je_load_density.utils.security.rate_limit_probe", "probe_rate_limit")
read_action_json = _lazy_command("je_load_density.utils.json.json_file.json_file", "read_action_json")
read_action_toml = _lazy_command("je_load_density.utils.json.json_file.toml_file", "read_action_toml")
read_action_yaml = _lazy_command("je_load_density.utils.json.json_file.yaml_file", "read_action_yaml")
read_audit_log = _lazy_command("je_load_density.utils.governance.audit_log", "read_audit_log")
render_prompt_text = _lazy_command("je_load_density.utils.ai.root_cause", "render_prompt_text")
render_ssrf_tasks = _lazy_command(_MODULE_UTILS_SECURITY_SSRF_CHECKS, "render_ssrf_tasks")
run_db_teardown = _lazy_command("je_load_density.utils.data.db_fixtures", "run_teardown")
run_owasp_checks = _lazy_command("je_load_density.utils.security.owasp_checks", "run_owasp_checks")
search_catalog = _lazy_command("je_load_density.utils.governance.test_catalog", "search_catalog")
search_runs_by_tag = _lazy_command(_MODULE_UTILS_GOVERNANCE_RUN_TAGGING, "search_runs_by_tag")
smuggling_attack_pack = _lazy_command(_MODULE_UTILS_SECURITY_SMUGGLING_CHECKS, "smuggling_attack_pack")
start_dashboard = _lazy_command("je_load_density.utils.dashboard.live_dashboard", "start_dashboard")
start_datadog_apm_exporter = _lazy_command(
    "je_load_density.utils.metrics.datadog_apm_exporter", "start_datadog_apm_exporter"
)
start_influxdb_sink = _lazy_command("je_load_density.utils.metrics.influxdb_sink", "start_influxdb_sink")
start_opentelemetry_exporter = _lazy_command(
    "je_load_density.utils.metrics.opentelemetry_exporter", "start_opentelemetry_exporter"
)
start_opentelemetry_tracing_exporter = _lazy_command(
    "je_load_density.utils.metrics.opentelemetry_tracing_exporter", "start_opentelemetry_tracing_exporter"
)
start_prometheus_exporter = _lazy_command(
    "je_load_density.utils.metrics.prometheus_exporter", "start_prometheus_exporter"
)
start_statsd_sink = _lazy_command("je_load_density.utils.metrics.statsd_sink", "start_statsd_sink")
start_stub_server = _lazy_command("je_load_density.utils.stub_server.stub_server", "start_stub_server")
start_test = _lazy_command("je_load_density.engine.entrypoints", "start_test")
stop_dashboard = _lazy_command("je_load_density.utils.dashboard.live_dashboard", "stop_dashboard")
stop_datadog_apm_exporter = _lazy_command(
    "je_load_density.utils.metrics.datadog_apm_exporter", "stop_datadog_apm_exporter"
)
stop_influxdb_sink = _lazy_command("je_load_density.utils.metrics.influxdb_sink", "stop_influxdb_sink")
stop_opentelemetry_exporter = _lazy_command(
    "je_load_density.utils.metrics.opentelemetry_exporter", "stop_opentelemetry_exporter"
)
stop_opentelemetry_tracing_exporter = _lazy_command(
    "je_load_density.utils.metrics.opentelemetry_tracing_exporter", "stop_opentelemetry_tracing_exporter"
)
stop_prometheus_exporter = _lazy_command(
    "je_load_density.utils.metrics.prometheus_exporter", "stop_prometheus_exporter"
)
stop_statsd_sink = _lazy_command("je_load_density.utils.metrics.statsd_sink", "stop_statsd_sink")
stop_stub_server = _lazy_command("je_load_density.utils.stub_server.stub_server", "stop_stub_server")
tag_run = _lazy_command(_MODULE_UTILS_GOVERNANCE_RUN_TAGGING, "tag_run")
toxiproxy_add_toxic = _lazy_command(_MODULE_UTILS_CHAOS_TOXIPROXY, "add_toxic")
toxiproxy_create_proxy = _lazy_command(_MODULE_UTILS_CHAOS_TOXIPROXY, "create_proxy")
toxiproxy_install_bandwidth = _lazy_command(_MODULE_UTILS_CHAOS_TOXIPROXY, "install_bandwidth")
toxiproxy_install_latency = _lazy_command(_MODULE_UTILS_CHAOS_TOXIPROXY, "install_latency")
toxiproxy_list_proxies = _lazy_command(_MODULE_UTILS_CHAOS_TOXIPROXY, "list_proxies")
toxiproxy_remove_proxies = _lazy_command(_MODULE_UTILS_CHAOS_TOXIPROXY, "remove_proxies")
toxiproxy_remove_toxic = _lazy_command(_MODULE_UTILS_CHAOS_TOXIPROXY, "remove_toxic")
toxiproxy_reset_all = _lazy_command(_MODULE_UTILS_CHAOS_TOXIPROXY, "reset_all")
trend_runs = _lazy_command("je_load_density.utils.regression.multi_run_trend", "trend_runs")
uninstall_failure_budget = _lazy_command("je_load_density.utils.reliability.failure_budget", "uninstall_failure_budget")
uninstall_network_conditioner = _lazy_command(
    "je_load_density.utils.reliability.network_conditioner", "uninstall_network_conditioner"
)
verify_share_link = _lazy_command("je_load_density.utils.governance.share_link", "verify_share_link")
write_action_toml = _lazy_command("je_load_density.utils.json.json_file.toml_file", "write_action_toml")
write_action_yaml = _lazy_command("je_load_density.utils.json.json_file.yaml_file", "write_action_yaml")


# Builtins: je_action_core's SAFE_BUILTINS allowlist, the same names every workspace framework registers
# (workspace X-12). The name stays exported here.
__all__ = ["SAFE_BUILTINS", "Executor", "add_command_to_executor", "execute_action", "execute_files", "executor"]

# The document key and error texts; the dispatch is je_action_core's (workspace L-6). Records are printed:
# a failure's repr and action to stderr, then every record's key and value to stdout.
_SETTINGS = ExecutorSettings(
    rules=ActionListRules(
        "load_density",
        error=LoadDensityTestExecuteException,
        missing_message=executor_list_error,
        not_list_message=executor_list_error,
        empty_message=executor_list_error,
    ),
    parser=LegacyActionParser(error=LoadDensityTestExecuteException, message=executor_data_error),
    reporter=PrintReporter(),
    read_json=read_action_json,
)


def _clear_records() -> dict:
    test_record_instance.clear_records()
    return {"status": "cleared"}


def _clear_resolver() -> dict:
    parameter_resolver.clear()
    return {"status": "cleared"}


def _lazy_start_socket_server(*args, **kwargs):
    from je_load_density.utils.socket_server.load_density_socket_server import (
        start_load_density_socket_server,
    )

    return start_load_density_socket_server(*args, **kwargs)


class Executor(ActionExecutor):
    """
    執行器 (Executor)
    Event-driven executor that runs LD_* actions plus safe builtins (je_action_core's executor).
    """

    def __init__(self) -> None:
        super().__init__(
            _SETTINGS,
            CommandRegistry(
                policy=CommandPolicy.FUNCTIONS_ONLY,
                rejection=lambda _name: LoadDensityTestExecuteException(add_command_exception_tag),
            ),
        )
        self.event_dict = {
            # Core
            "LD_start_test": start_test,
            "LD_execute_action": self.execute_action,
            "LD_execute_files": self.execute_files,
            "LD_add_package_to_executor": package_manager.add_package_to_executor,
            # Reports
            "LD_generate_html": generate_html,
            "LD_generate_html_report": generate_html_report,
            "LD_generate_json": generate_json,
            "LD_generate_json_report": generate_json_report,
            "LD_generate_xml": generate_xml,
            "LD_generate_xml_report": generate_xml_report,
            "LD_generate_csv_report": generate_csv_report,
            "LD_generate_junit_report": generate_junit_report,
            "LD_generate_summary_report": generate_summary_report,
            "LD_generate_chart_report": generate_chart_report,
            "LD_summary": build_summary,
            # Test record persistence
            "LD_persist_records": persist_records,
            "LD_list_runs": list_runs,
            "LD_fetch_run_records": fetch_run_records,
            "LD_clear_records": _clear_records,
            # Parameter resolver
            "LD_register_variable": register_variable,
            "LD_register_variables": register_variables,
            "LD_register_csv_source": register_csv_source,
            "LD_register_csv_sources": register_csv_sources,
            "LD_clear_resolver": _clear_resolver,
            # Recording / replay
            "LD_load_har": load_har,
            "LD_har_to_tasks": har_to_tasks,
            "LD_har_to_action_json": har_to_action_json,
            "LD_load_postman_collection": load_postman_collection,
            "LD_postman_to_tasks": postman_to_tasks,
            "LD_postman_to_action_json": postman_to_action_json,
            "LD_load_openapi": load_openapi,
            "LD_openapi_to_tasks": openapi_to_tasks,
            "LD_openapi_to_action_json": openapi_to_action_json,
            "LD_curl_to_task": curl_to_task,
            "LD_load_k6_script": load_k6_script,
            "LD_k6_script_to_tasks": k6_script_to_tasks,
            "LD_k6_script_to_action_json": k6_script_to_action_json,
            "LD_load_jmeter_jmx": load_jmeter_jmx,
            "LD_jmeter_to_tasks": jmeter_to_tasks,
            "LD_jmeter_to_action_json": jmeter_to_action_json,
            # Reliability
            "LD_install_failure_budget": install_failure_budget,
            "LD_uninstall_failure_budget": uninstall_failure_budget,
            "LD_install_network_conditioner": install_network_conditioner,
            "LD_uninstall_network_conditioner": uninstall_network_conditioner,
            # Glue
            "LD_start_dashboard": start_dashboard,
            "LD_stop_dashboard": stop_dashboard,
            "LD_start_statsd_sink": start_statsd_sink,
            "LD_stop_statsd_sink": stop_statsd_sink,
            "LD_post_slack_summary": post_slack_summary,
            "LD_post_teams_summary": post_teams_summary,
            # Quality / DX
            "LD_lint_action": lint_action,
            "LD_lint_action_file": lint_action_file,
            "LD_export_schema": export_schema,
            "LD_emit_github_annotations": emit_github_annotations,
            # SLA / regression
            "LD_evaluate_sla": evaluate_sla,
            "LD_assert_sla": assert_sla,
            "LD_diff_runs": diff_runs,
            # Parameter resolver (DB extension)
            "LD_register_db_source": register_db_source,
            "LD_register_db_sources": register_db_sources,
            # Metrics exporters
            "LD_start_prometheus_exporter": start_prometheus_exporter,
            "LD_stop_prometheus_exporter": stop_prometheus_exporter,
            "LD_start_influxdb_sink": start_influxdb_sink,
            "LD_stop_influxdb_sink": stop_influxdb_sink,
            "LD_start_opentelemetry_exporter": start_opentelemetry_exporter,
            "LD_stop_opentelemetry_exporter": stop_opentelemetry_exporter,
            # Control socket
            "LD_start_socket_server": _lazy_start_socket_server,
            # New report formats
            "LD_generate_histogram_report": generate_histogram_report,
            "LD_generate_pdf_report": generate_pdf_report,
            "LD_generate_allure_report": generate_allure_report,
            # YAML / TOML loaders
            "LD_read_action_yaml": read_action_yaml,
            "LD_write_action_yaml": write_action_yaml,
            "LD_read_action_toml": read_action_toml,
            "LD_write_action_toml": write_action_toml,
            # Action formatter / generator
            "LD_format_action_document": format_action_document,
            "LD_format_action_file": format_action_file,
            "LD_format_action_string": format_action_string,
            "LD_generate_from_openapi": generate_from_openapi,
            "LD_generate_from_curls": generate_from_curls,
            # Trend & clustering
            "LD_trend_runs": trend_runs,
            "LD_cluster_errors": cluster_errors,
            # Notifiers (new)
            "LD_post_pagerduty_event": post_pagerduty_event,
            "LD_post_opsgenie_alert": post_opsgenie_alert,
            "LD_post_gitlab_mr_summary": post_gitlab_mr_summary,
            # OTel tracing & Datadog APM
            "LD_start_opentelemetry_tracing_exporter": start_opentelemetry_tracing_exporter,
            "LD_stop_opentelemetry_tracing_exporter": stop_opentelemetry_tracing_exporter,
            "LD_start_datadog_apm_exporter": start_datadog_apm_exporter,
            "LD_stop_datadog_apm_exporter": stop_datadog_apm_exporter,
            # Stub server
            "LD_start_stub_server": start_stub_server,
            "LD_stop_stub_server": stop_stub_server,
            # Security
            "LD_mutate_string": mutate_string,
            "LD_mutate_json": mutate_json,
            "LD_expand_task_fuzz": expand_task_fuzz,
            "LD_run_owasp_checks": run_owasp_checks,
            # Chaos engineering
            "LD_toxiproxy_create_proxy": toxiproxy_create_proxy,
            "LD_toxiproxy_list_proxies": toxiproxy_list_proxies,
            "LD_toxiproxy_add_toxic": toxiproxy_add_toxic,
            "LD_toxiproxy_remove_toxic": toxiproxy_remove_toxic,
            "LD_toxiproxy_install_latency": toxiproxy_install_latency,
            "LD_toxiproxy_install_bandwidth": toxiproxy_install_bandwidth,
            "LD_toxiproxy_reset_all": toxiproxy_reset_all,
            "LD_toxiproxy_remove_proxies": toxiproxy_remove_proxies,
            "LD_chaos_apply_manifest": chaos_apply_manifest,
            "LD_chaos_delete_manifest": chaos_delete_manifest,
            "LD_chaos_network_delay": chaos_network_delay,
            # AI
            "LD_build_root_cause_prompt": build_root_cause_prompt,
            "LD_render_prompt_text": render_prompt_text,
            "LD_find_breaking_point": find_breaking_point,
            "LD_calibrate_sla": calibrate_sla,
            # New reports
            "LD_generate_excel_report": generate_excel_report,
            "LD_generate_sarif_report": generate_sarif_report,
            "LD_generate_cyclonedx_report": generate_cyclonedx_report,
            "LD_generate_service_map": generate_service_map,
            "LD_generate_cost_report": generate_cost_report,
            # Data / state
            "LD_pii_scrub": pii_scrub,
            "LD_pii_scrub_string": pii_scrub_string,
            "LD_build_user": build_user,
            "LD_build_user_pool": build_user_pool,
            "LD_apply_db_fixture": apply_db_fixture,
            "LD_run_db_teardown": run_db_teardown,
            # Governance
            "LD_index_catalog": index_catalog,
            "LD_search_catalog": search_catalog,
            "LD_tag_run": tag_run,
            "LD_list_tags": list_tags,
            "LD_search_runs_by_tag": search_runs_by_tag,
            "LD_append_audit_entry": append_audit_entry,
            "LD_read_audit_log": read_audit_log,
            "LD_issue_share_link": issue_share_link,
            "LD_verify_share_link": verify_share_link,
            # Canary
            "LD_canary_verdict": canary_verdict,
            # Recording
            "LD_cdp_discover_targets": cdp_discover_targets,
            "LD_cdp_capture_session": capture_cdp_session,
            "LD_cdp_capture_to_har": capture_cdp_to_har,
            # Security: JWT attacks
            "LD_craft_alg_none_token": craft_alg_none_token,
            "LD_craft_alg_confusion_token": craft_alg_confusion_token,
            "LD_craft_expired_token": craft_expired_token,
            "LD_craft_kid_traversal_token": craft_kid_traversal_token,
            "LD_craft_jwt_attack_pack": craft_jwt_attack_pack,
            # Security: GraphQL
            "LD_graphql_introspection_payload": build_introspection_payload,
            "LD_graphql_depth_attack": build_depth_attack,
            "LD_graphql_alias_batching": build_alias_batching_attack,
            "LD_graphql_attack_pack": graphql_attack_pack,
            # Security: SSRF
            "LD_ssrf_targets": build_ssrf_targets,
            "LD_render_ssrf_tasks": render_ssrf_tasks,
            "LD_find_metadata_leak": find_metadata_leak,
            # Security: smuggling
            "LD_smuggling_cl_te": build_cl_te,
            "LD_smuggling_te_cl": build_te_cl,
            "LD_smuggling_te_te": build_te_te,
            "LD_smuggling_attack_pack": smuggling_attack_pack,
            # Security: rate limit probe
            "LD_probe_rate_limit": probe_rate_limit,
        }

        self.event_dict.update(safe_builtin_commands())

    @staticmethod
    def set_allow_arbitrary_packages(enabled: bool) -> None:
        """
        Allow (True) or refuse (False) ``LD_add_package_to_executor`` for packages outside the allowlist.
        Python only, never an action command, so an action file cannot open its own gate. Until it is
        called, any package loads with a ``DeprecationWarning``.
        """
        package_manager.set_allow_arbitrary_packages(enabled)

    @staticmethod
    def allow_packages(*packages: str) -> None:
        """Add packages, and their submodules, to the allowlist of ``LD_add_package_to_executor``."""
        package_manager.allow_packages(*packages)


executor = Executor()
package_manager.executor = executor


def add_command_to_executor(command_dict: dict[str, Any]) -> None:
    """Add functions or methods as commands; the first other value raises (the ones before it stay)."""
    executor.add_command_to_executor(command_dict)


def execute_action(action_list: list) -> dict[str, Any]:
    return executor.execute_action(action_list)


def execute_files(execute_files_list: list[str]) -> list[dict[str, Any]]:
    return executor.execute_files(execute_files_list)
