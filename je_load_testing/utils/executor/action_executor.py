import sys

from je_load_testing.utils.exception.exception import JELoadingTestExecuteException
from je_load_testing.wrapper.env_with_user.wrapper_env_and_user import loading_test_with_user
from je_load_testing.utils.exception.exception_tag import executor_data_error
from je_load_testing.utils.exception.exception_tag import executor_list_error
from je_load_testing.utils.json.json_file.json_file import read_action_json


event_dict = {
    "loading_test_with_user": loading_test_with_user
}


def execute_event(action: list):
    """
    :param action: execute action
    :return: what event return
    """
    event = event_dict.get(action[0])
    if len(action) == 2:
        return event(**action[1])
    else:
        raise JELoadingTestExecuteException(executor_data_error)


def execute_action(action_list: list):
    """
    :param action_list: like this structure
    [
        ["method on event_dict", {"param": params}],
        ["method on event_dict", {"param": params}]
    ]
    for loop and use execute_event function to execute
    :return: recode string, response as list
    """
    execute_record_string = ""
    event_response_list = []
    try:
        if len(action_list) > 0 or type(action_list) is not list:
            for action in action_list:
                event_response = execute_event(action)
                print("execute: ", str(action))
                execute_record_string = "".join(execute_record_string)
                event_response_list.append(event_response)
        else:
            raise JELoadingTestExecuteException(executor_list_error)
        return execute_record_string, event_response_list
    except Exception as error:
        print(repr(error), file=sys.stderr)


def execute_files(execute_files_list: list):
    """
    :param execute_files_list: list include execute files path
    :return: every execute detail as list
    """
    execute_detail_list = list()
    for file in execute_files_list:
        execute_detail_list.append(execute_action(read_action_json(file)))
    return execute_detail_list
