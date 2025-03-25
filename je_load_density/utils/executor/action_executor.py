import builtins
import sys
import types
from inspect import getmembers, isbuiltin
from typing import Union, Any

from je_load_density.utils.exception.exception_tags import executor_data_error, add_command_exception_tag
from je_load_density.utils.exception.exception_tags import executor_list_error
from je_load_density.utils.exception.exceptions import LoadDensityTestExecuteException
from je_load_density.utils.generate_report.generate_html_report import generate_html, generate_html_report
from je_load_density.utils.generate_report.generate_json_report import generate_json, generate_json_report
from je_load_density.utils.generate_report.generate_xml_report import generate_xml, generate_xml_report
from je_load_density.utils.json.json_file.json_file import read_action_json
from je_load_density.utils.package_manager.package_manager_class import package_manager
from je_load_density.wrapper.start_wrapper.start_test import start_test


class Executor(object):

    def __init__(self):
        self.event_dict = {
            "LD_start_test": start_test,
            "LD_generate_html": generate_html,
            "LD_generate_html_report": generate_html_report,
            "LD_generate_json": generate_json,
            "LD_generate_json_report": generate_json_report,
            "LD_generate_xml": generate_xml,
            "LD_generate_xml_report": generate_xml_report,
            # Execute
            "LD_execute_action": self.execute_action,
            "LD_execute_files": self.execute_files,
            "LD_add_package_to_executor": package_manager.add_package_to_executor,
        }
        # get all builtin function and add to event dict
        for function in getmembers(builtins, isbuiltin):
            self.event_dict.update({str(function[0]): function[1]})

    def _execute_event(self, action: list):
        """
        :param action: execute action
        :return: what event return
        """
        event = self.event_dict.get(action[0])
        if len(action) == 2:
            if isinstance(action[1], dict):
                return event(**action[1])
            else:
                return event(*action[1])
        elif len(action) == 1:
            return event()
        else:
            raise LoadDensityTestExecuteException(executor_data_error + " " + str(action))

    def execute_action(self, action_list: [list, dict]) -> dict:
        """
        execute all action in action list
        :param action_list: like this structure
        [
            ["method on event_dict", {"param": params}],
            ["method on event_dict", {"param": params}]
        ]
        for loop and use execute_event function to execute
        :return: recode string, response as list
        """
        if isinstance(action_list, dict):
            action_list = action_list.get("load_density", None)
            if action_list is None:
                raise LoadDensityTestExecuteException(executor_list_error)
        execute_record_dict = dict()
        try:
            if len(action_list) == 0 or isinstance(action_list, list) is False:
                raise LoadDensityTestExecuteException(executor_list_error)
        except Exception as error:
            print(repr(error), file=sys.stderr)
        for action in action_list:
            try:
                event_response = self._execute_event(action)
                execute_record = "execute: " + str(action)
                execute_record_dict.update({execute_record: event_response})
            except Exception as error:
                print(repr(error), file=sys.stderr)
                print(action, file=sys.stderr)
                execute_record = "execute: " + str(action)
                execute_record_dict.update({execute_record: repr(error)})
        for key, value in execute_record_dict.items():
            print(key)
            print(value)
        return execute_record_dict

    def execute_files(self, execute_files_list: list):
        """
        execute action on all file in execute_files_list
        :param execute_files_list: list include execute files path
        :return: every execute detail as list
        """
        execute_detail_list = list()
        for file in execute_files_list:
            execute_detail_list.append(self.execute_action(read_action_json(file)))
        return execute_detail_list

executor = Executor()
package_manager.executor = executor


def add_command_to_executor(command_dict: dict):
    for command_name, command in command_dict.items():
        if isinstance(command, (types.MethodType, types.FunctionType)):
            executor.event_dict.update({command_name: command})
        else:
            raise LoadDensityTestExecuteException(add_command_exception_tag)


def execute_action(action_list: list) -> dict:
    return executor.execute_action(action_list)


def execute_files(execute_files_list: list) -> list:
    return executor.execute_files(execute_files_list)
