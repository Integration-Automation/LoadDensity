import builtins
import sys
import types
from inspect import getmembers, isbuiltin
from typing import Union, Any

from je_load_density.utils.exception.exception_tags import (
    executor_data_error,
    add_command_exception_tag,
    executor_list_error,
)
from je_load_density.utils.exception.exceptions import LoadDensityTestExecuteException
from je_load_density.utils.generate_report.generate_html_report import (
    generate_html,
    generate_html_report,
)
from je_load_density.utils.generate_report.generate_json_report import (
    generate_json,
    generate_json_report,
)
from je_load_density.utils.generate_report.generate_xml_report import (
    generate_xml,
    generate_xml_report,
)
from je_load_density.utils.json.json_file.json_file import read_action_json
from je_load_density.utils.package_manager.package_manager_class import package_manager
from je_load_density.wrapper.start_wrapper.start_test import start_test


class Executor:
    """
    執行器 (Executor)
    Event-driven executor

    提供事件字典 (event_dict)，可根據動作名稱執行對應函式，
    並支援批次執行與檔案驅動。
    Provides an event dictionary to execute functions by name,
    supporting batch execution and file-driven execution.
    """

    def __init__(self) -> None:
        # 初始化事件字典 (Initialize event dictionary)
        self.event_dict: dict[str, Any] = {
            "LD_start_test": start_test,
            "LD_generate_html": generate_html,
            "LD_generate_html_report": generate_html_report,
            "LD_generate_json": generate_json,
            "LD_generate_json_report": generate_json_report,
            "LD_generate_xml": generate_xml,
            "LD_generate_xml_report": generate_xml_report,
            # Executor internal methods
            "LD_execute_action": self.execute_action,
            "LD_execute_files": self.execute_files,
            "LD_add_package_to_executor": package_manager.add_package_to_executor,
        }

        # 將所有 Python 內建函式加入事件字典
        # Add all Python built-in functions to event_dict
        for name, func in getmembers(builtins, isbuiltin):
            self.event_dict[name] = func

    def _execute_event(self, action: list) -> Any:
        """
        執行單一事件
        Execute a single event

        :param action: 事件結構，例如 ["function_name", {"param": value}]
        :return: 事件回傳值 (return value of executed event)
        """
        event = self.event_dict.get(action[0])
        if event is None:
            raise LoadDensityTestExecuteException(executor_data_error + " " + str(action))

        if len(action) == 2:
            if isinstance(action[1], dict):
                return event(**action[1])
            else:
                return event(*action[1])
        elif len(action) == 1:
            return event()
        else:
            raise LoadDensityTestExecuteException(executor_data_error + " " + str(action))

    def execute_action(self, action_list: Union[list, dict]) -> dict[str, Any]:
        """
        執行多個事件
        Execute multiple actions

        :param action_list: 事件列表，例如：
            [
                ["LD_start_test", {"param": value}],
                ["LD_generate_json", {"param": value}]
            ]
        :return: 執行紀錄字典 (execution record dict)
        """
        if isinstance(action_list, dict):
            action_list = action_list.get("load_density", None)
            if action_list is None:
                raise LoadDensityTestExecuteException(executor_list_error)

        execute_record_dict: dict[str, Any] = {}

        try:
            if not isinstance(action_list, list) or len(action_list) == 0:
                raise LoadDensityTestExecuteException(executor_list_error)
        except Exception as error:
            print(repr(error), file=sys.stderr)

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

        # 輸出執行結果 (Print execution results)
        for key, value in execute_record_dict.items():
            print(key)
            print(value)

        return execute_record_dict

    def execute_files(self, execute_files_list: list[str]) -> list[dict[str, Any]]:
        """
        執行檔案中的事件
        Execute actions from files

        :param execute_files_list: 檔案路徑列表 (list of file paths)
        :return: 每個檔案的執行結果列表 (list of execution results per file)
        """
        execute_detail_list: list[dict[str, Any]] = []
        for file in execute_files_list:
            execute_detail_list.append(self.execute_action(read_action_json(file)))
        return execute_detail_list


# 建立全域執行器 (Global executor instance)
executor = Executor()
package_manager.executor = executor


def add_command_to_executor(command_dict: dict[str, Any]) -> None:
    """
    新增自訂命令到執行器
    Add custom commands to executor

    :param command_dict: {command_name: function}
    """
    for command_name, command in command_dict.items():
        if isinstance(command, (types.MethodType, types.FunctionType)):
            executor.event_dict[command_name] = command
        else:
            raise LoadDensityTestExecuteException(add_command_exception_tag)


def execute_action(action_list: list) -> dict[str, Any]:
    """全域執行事件 (Global execute action)"""
    return executor.execute_action(action_list)


def execute_files(execute_files_list: list[str]) -> list[dict[str, Any]]:
    """全域執行檔案事件 (Global execute files)"""
    return executor.execute_files(execute_files_list)