import builtins
import sys
import types
from inspect import getmembers, isbuiltin
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
from je_load_density.utils.generate_report.generate_chart_report import (
    generate_chart_report,
)
from je_load_density.utils.generate_report.generate_xml_report import (
    generate_xml,
    generate_xml_report,
)
from je_load_density.utils.json.json_file.json_file import read_action_json
from je_load_density.utils.metrics.influxdb_sink import (
    start_influxdb_sink,
    stop_influxdb_sink,
)
from je_load_density.utils.metrics.opentelemetry_exporter import (
    start_opentelemetry_exporter,
    stop_opentelemetry_exporter,
)
from je_load_density.utils.metrics.prometheus_exporter import (
    start_prometheus_exporter,
    stop_prometheus_exporter,
)
from je_load_density.utils.package_manager.package_manager_class import package_manager
from je_load_density.utils.ci_annotations.github_actions import emit_github_annotations
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
from je_load_density.utils.dashboard.live_dashboard import (
    start_dashboard,
    stop_dashboard,
)
from je_load_density.utils.metrics.statsd_sink import (
    start_statsd_sink,
    stop_statsd_sink,
)
from je_load_density.utils.notifier.slack import post_slack_summary
from je_load_density.utils.notifier.teams import post_teams_summary
from je_load_density.utils.test_record.sqlite_persistence import (
    fetch_run_records,
    list_runs,
    persist_records,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.wrapper.start_wrapper.start_test import start_test

_UNSAFE_BUILTINS = frozenset({
    "eval", "exec", "compile", "__import__",
    "breakpoint", "open", "input",
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
        }

        for name, func in getmembers(builtins, isbuiltin):
            if name in _UNSAFE_BUILTINS:
                continue
            self.event_dict[name] = func

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
