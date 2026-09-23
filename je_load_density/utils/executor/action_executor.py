import builtins
import sys
import types
from typing import Any, Union

from je_load_density.utils.exception.exception_tags import (
    add_command_exception_tag,
    executor_data_error,
    executor_list_error,
)
from je_load_density.utils.exception.exceptions import LoadDensityTestExecuteException
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
from je_load_density.utils.generate_report.generate_xml_report import (
    generate_xml,
    generate_xml_report,
)
from je_load_density.utils.chaos.chaos_mesh import (
    apply_manifest as chaos_apply_manifest,
    build_network_delay as chaos_network_delay,
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
from je_load_density.utils.json.json_file.json_file import read_action_json
from je_load_density.utils.json.json_file.toml_file import (
    read_action_toml,
    write_action_toml,
)
from je_load_density.utils.json.json_file.yaml_file import (
    read_action_yaml,
    write_action_yaml,
)
from je_load_density.utils.stub_server.stub_server import (
    start_stub_server,
    stop_stub_server,
)
from je_load_density.utils.metrics.influxdb_sink import (
    start_influxdb_sink,
    stop_influxdb_sink,
)
from je_load_density.utils.metrics.datadog_apm_exporter import (
    start_datadog_apm_exporter,
    stop_datadog_apm_exporter,
)
from je_load_density.utils.metrics.opentelemetry_exporter import (
    start_opentelemetry_exporter,
    stop_opentelemetry_exporter,
)
from je_load_density.utils.metrics.opentelemetry_tracing_exporter import (
    start_opentelemetry_tracing_exporter,
    stop_opentelemetry_tracing_exporter,
)
from je_load_density.utils.metrics.prometheus_exporter import (
    start_prometheus_exporter,
    stop_prometheus_exporter,
)
from je_load_density.utils.package_manager.package_manager_class import package_manager
from je_load_density.utils.ci_annotations.github_actions import emit_github_annotations
from je_load_density.utils.action_generator.generate import (
    generate_from_curls,
    generate_from_openapi,
)
from je_load_density.utils.linter.action_formatter import (
    format_action_document,
    format_action_file,
    format_action_string,
)
from je_load_density.utils.linter.action_linter import lint_action, lint_action_file
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_source,
    register_csv_sources,
    register_db_source,
    register_db_sources,
    register_variable,
    register_variables,
)
from je_load_density.utils.regression.diff import diff_runs
from je_load_density.utils.regression.error_clustering import cluster_errors
from je_load_density.utils.regression.multi_run_trend import trend_runs
from je_load_density.utils.schema.action_schema import export_schema
from je_load_density.utils.sla.sla_gates import assert_sla, evaluate_sla
from je_load_density.utils.recording.curl_importer import curl_to_task
from je_load_density.utils.recording.har_importer import (
    har_to_action_json,
    har_to_tasks,
    load_har,
)
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
from je_load_density.utils.reliability.failure_budget import (
    install_failure_budget,
    uninstall_failure_budget,
)
from je_load_density.utils.reliability.network_conditioner import (
    install_network_conditioner,
    uninstall_network_conditioner,
)
from je_load_density.utils.ai.auto_baseline import calibrate_sla
from je_load_density.utils.ai.root_cause import build_root_cause_prompt, render_prompt_text
from je_load_density.utils.ai.smart_shape import find_breaking_point
from je_load_density.utils.ci_annotations.canary_analysis import canary_verdict
from je_load_density.utils.dashboard.live_dashboard import (
    start_dashboard,
    stop_dashboard,
)
from je_load_density.utils.data.db_fixtures import apply_fixture as apply_db_fixture
from je_load_density.utils.data.db_fixtures import run_teardown as run_db_teardown
from je_load_density.utils.data.factory import build_user, build_user_pool
from je_load_density.utils.data.pii_anonymizer import scrub as pii_scrub
from je_load_density.utils.data.pii_anonymizer import scrub_string as pii_scrub_string
from je_load_density.utils.generate_report.generate_cost_report import (
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
    generate_service_map,
)
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
from je_load_density.utils.recording.cdp_capture import (
    capture_cdp_session,
    capture_cdp_to_har,
    discover_targets as cdp_discover_targets,
)
from je_load_density.utils.security.fuzz import expand_task_fuzz, mutate_json, mutate_string
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
from je_load_density.utils.security.owasp_checks import run_owasp_checks
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
from je_load_density.utils.metrics.statsd_sink import (
    start_statsd_sink,
    stop_statsd_sink,
)
from je_load_density.utils.notifier.gitlab import post_gitlab_mr_summary
from je_load_density.utils.notifier.opsgenie import post_opsgenie_alert
from je_load_density.utils.notifier.pagerduty import post_pagerduty_event
from je_load_density.utils.notifier.slack import post_slack_summary
from je_load_density.utils.notifier.teams import post_teams_summary
from je_load_density.utils.test_record.sqlite_persistence import (
    fetch_run_records,
    list_runs,
    persist_records,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.wrapper.start_wrapper.start_test import start_test

# Allowlist, not a blocklist: registering "everything except the dangerous ones"
# hands action JSON whatever a future Python adds, and the earlier list still let
# `getattr` / `setattr` / `vars` / `globals` through, which walk to anything the
# process can reach. These are the same names MailThunder's executor allows, so an
# action list behaves the same across the workspace's frameworks (workspace X-12).
SAFE_BUILTINS = frozenset({
    "abs", "all", "any", "ascii", "bin", "callable", "chr", "divmod",
    "format", "hash", "hex", "len", "max", "min", "oct", "ord", "pow",
    "print", "repr", "round", "sorted", "sum",
})


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


class Executor:
    """
    執行器 (Executor)
    Event-driven executor that runs LD_* actions plus safe builtins.
    """

    def __init__(self) -> None:
        self.event_dict: dict[str, Any] = {
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

        for name in sorted(SAFE_BUILTINS):
            self.event_dict[name] = getattr(builtins, name)

    def _execute_event(self, action: list) -> Any:
        event = self.event_dict.get(action[0])
        if event is None:
            raise LoadDensityTestExecuteException(executor_data_error + " " + str(action))

        if len(action) == 2:
            if isinstance(action[1], dict):
                return event(**action[1])
            return event(*action[1])
        if len(action) == 1:
            return event()
        raise LoadDensityTestExecuteException(executor_data_error + " " + str(action))

    def execute_action(self, action_list: Union[list, dict]) -> dict[str, Any]:
        if isinstance(action_list, dict):
            action_list = action_list.get("load_density", None)
            if action_list is None:
                raise LoadDensityTestExecuteException(executor_list_error)

        if not isinstance(action_list, list) or len(action_list) == 0:
            raise LoadDensityTestExecuteException(executor_list_error)

        execute_record_dict: dict[str, Any] = {}
        for action in action_list:
            try:
                event_response = self._execute_event(action)
                execute_record = f"execute: {action}"
                execute_record_dict[execute_record] = event_response
            except Exception as error:
                print(repr(error), file=sys.stderr)
                print(action, file=sys.stderr)
                execute_record = f"execute: {action}"
                execute_record_dict[execute_record] = repr(error)

        for key, value in execute_record_dict.items():
            print(key)
            print(value)

        return execute_record_dict

    def execute_files(self, execute_files_list: list[str]) -> list[dict[str, Any]]:
        return [self.execute_action(read_action_json(path)) for path in execute_files_list]


executor = Executor()
package_manager.executor = executor


def add_command_to_executor(command_dict: dict[str, Any]) -> None:
    for command_name, command in command_dict.items():
        if isinstance(command, (types.MethodType, types.FunctionType)):
            executor.event_dict[command_name] = command
        else:
            raise LoadDensityTestExecuteException(add_command_exception_tag)


def execute_action(action_list: list) -> dict[str, Any]:
    return executor.execute_action(action_list)


def execute_files(execute_files_list: list[str]) -> list[dict[str, Any]]:
    return executor.execute_files(execute_files_list)
