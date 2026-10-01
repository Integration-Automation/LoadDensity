from sys import stderr

from je_action_core import CallbackErrorPolicy, CallbackSettings, CommandRegistry
from je_action_core import CallbackFunctionExecutor as _CoreCallbackExecutor

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


def _print_error(message: str) -> None:
    print(message, file=stderr)


_SETTINGS = CallbackSettings(
    error=CallbackExecutorException,
    unknown_trigger_message=get_bad_trigger_function,
    bad_method_message=get_bad_trigger_method,
    on_error=CallbackErrorPolicy.RAISE,  # the error is printed to stderr, then raised
    log_error=_print_error,
)


class CallbackFunctionExecutor(_CoreCallbackExecutor):
    """
    回呼函式執行器
    Callback Function Executor

    提供事件觸發與回呼機制，先執行指定的 trigger function，
    再執行 callback function。
    Provides a mechanism to trigger a function from event_dict,
    then execute a callback function.
    """

    def __init__(self) -> None:
        super().__init__(CommandRegistry(), _SETTINGS)
        # 事件字典，定義可觸發的函式
        # Event dictionary, defines available trigger functions
        self.event_dict = {
            "user_test": start_test,
            "LD_generate_html": generate_html,
            "LD_generate_html_report": generate_html_report,
            "LD_generate_json": generate_json,
            "LD_generate_json_report": generate_json_report,
            "LD_generate_xml": generate_xml,
            "LD_generate_xml_report": generate_xml_report,
        }


# 建立全域執行器實例
# Create global executor instance
callback_executor = CallbackFunctionExecutor()
