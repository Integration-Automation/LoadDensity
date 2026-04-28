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
    register_variable,
    register_variables,
    resolve,
)

# Recording / replay
from je_load_density.utils.recording.har_importer import (
    har_to_action_json,
    har_to_tasks,
    load_har,
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
    "build_summary",
    "read_action_json",
    "start_load_density_socket_server",
    "SequentialTaskSet", "task", "TaskSet",
    "callback_executor", "create_project_dir",
    "parameter_resolver", "resolve",
    "register_variable", "register_variables",
    "register_csv_source", "register_csv_sources",
    "har_to_action_json", "har_to_tasks", "load_har",
    "persist_records", "list_runs", "fetch_run_records",
    "start_prometheus_exporter", "stop_prometheus_exporter",
    "start_influxdb_sink", "stop_influxdb_sink",
    "start_opentelemetry_exporter", "stop_opentelemetry_exporter",
]
