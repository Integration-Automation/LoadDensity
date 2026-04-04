import pytest

from je_load_density.utils.callback.callback_function_executor import CallbackFunctionExecutor
from je_load_density.utils.exception.exceptions import CallbackExecutorException


def _dummy_trigger(**kwargs):
    return kwargs.get("value", 42)


def _dummy_callback(*args, **kwargs):
    pass


class TestCallbackFunctionExecutor:

    def _make_executor(self):
        exe = CallbackFunctionExecutor()
        exe.event_dict["dummy"] = _dummy_trigger
        return exe

    def test_trigger_and_callback_kwargs(self):
        exe = self._make_executor()
        result = exe.callback_function(
            trigger_function_name="dummy",
            callback_function=_dummy_callback,
            callback_function_param={"key": "val"},
            callback_param_method="kwargs",
            value=99,
        )
        assert result == 99

    def test_trigger_and_callback_args(self):
        collected = []
        exe = self._make_executor()
        result = exe.callback_function(
            trigger_function_name="dummy",
            callback_function=lambda *a: collected.extend(a),
            callback_function_param=["hello", "world"],
            callback_param_method="args",
            value=10,
        )
        assert result == 10
        assert collected == ["hello", "world"]

    def test_callback_no_params(self):
        called = []
        exe = self._make_executor()
        result = exe.callback_function(
            trigger_function_name="dummy",
            callback_function=lambda: called.append(True),
            value=5,
        )
        assert result == 5
        assert called == [True]

    def test_invalid_trigger_function_raises(self):
        exe = self._make_executor()
        with pytest.raises(CallbackExecutorException):
            exe.callback_function(
                trigger_function_name="nonexistent",
                callback_function=_dummy_callback,
            )

    def test_invalid_param_method_raises(self):
        exe = self._make_executor()
        with pytest.raises(CallbackExecutorException):
            exe.callback_function(
                trigger_function_name="dummy",
                callback_function=_dummy_callback,
                callback_function_param={"k": "v"},
                callback_param_method="invalid",
            )

    def test_default_event_dict_keys(self):
        exe = CallbackFunctionExecutor()
        assert "user_test" in exe.event_dict
        assert "LD_generate_html" in exe.event_dict
        assert "LD_generate_json" in exe.event_dict
        assert "LD_generate_xml" in exe.event_dict
