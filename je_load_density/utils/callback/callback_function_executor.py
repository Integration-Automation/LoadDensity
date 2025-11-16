import typing
from sys import stderr

from je_load_density.utils.exception.exception_tags import (
    get_bad_trigger_function,
    get_bad_trigger_method,
)
from je_load_density.utils.exception.exceptions import CallbackExecutorException
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
from je_load_density.wrapper.start_wrapper.start_test import start_test


class CallbackFunctionExecutor:
    """
    回呼函式執行器
    Callback Function Executor

    提供事件觸發與回呼機制，先執行指定的 trigger function，
    再執行 callback function。
    Provides a mechanism to trigger a function from event_dict,
    then execute a callback function.
    """

    def __init__(self) -> None:
        # 事件字典，定義可觸發的函式
        # Event dictionary, defines available trigger functions
        self.event_dict: dict[str, typing.Callable] = {
            "user_test": start_test,
            "LD_generate_html": generate_html,
            "LD_generate_html_report": generate_html_report,
            "LD_generate_json": generate_json,
            "LD_generate_json_report": generate_json_report,
            "LD_generate_xml": generate_xml,
            "LD_generate_xml_report": generate_xml_report,
        }

    def callback_function(
        self,
        trigger_function_name: str,
        callback_function: typing.Callable,
        callback_function_param: typing.Optional[typing.Union[dict, list]] = None,
        callback_param_method: str = "kwargs",
        **kwargs,
    ) -> typing.Any:
        """
        執行事件函式並呼叫回呼函式
        Execute trigger function and then call callback function

        :param trigger_function_name: 事件函式名稱 (must exist in event_dict)
        :param callback_function: 回呼函式 (callback function to execute)
        :param callback_function_param: 回呼函式參數 (dict for kwargs, list for args)
        :param callback_param_method: 參數傳遞方式 ("kwargs" or "args")
        :param kwargs: 傳給事件函式的參數 (parameters for trigger function)
        :return: 事件函式的回傳值 (return value of trigger function)
        """
        try:
            # 檢查事件函式是否存在
            # Validate trigger function existence
            if trigger_function_name not in self.event_dict:
                raise CallbackExecutorException(get_bad_trigger_function)

            # 執行事件函式
            # Execute trigger function
            execute_return_value = self.event_dict[trigger_function_name](**kwargs)

            # 執行回呼函式
            # Execute callback function
            if callback_function_param is not None:
                if callback_param_method not in ["kwargs", "args"]:
                    raise CallbackExecutorException(get_bad_trigger_method)
                if callback_param_method == "kwargs":
                    callback_function(**callback_function_param)
                else:
                    callback_function(*callback_function_param)
            else:
                callback_function()

            return execute_return_value

        except Exception as error:
            # 目前只輸出錯誤，可以改成 logging 或 raise
            # Currently prints error; can be replaced with logging or re-raise
            print(repr(error), file=stderr)


# 建立全域執行器實例
# Create global executor instance
callback_executor = CallbackFunctionExecutor()