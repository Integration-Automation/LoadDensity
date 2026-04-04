import json
import os

import pytest

from je_load_density.utils.executor.action_executor import Executor, add_command_to_executor
from je_load_density.utils.exception.exceptions import LoadDensityTestExecuteException


def _sample_func(a=0, b=0):
    return a + b


class TestExecutor:

    def _make_executor(self):
        exe = Executor()
        exe.event_dict["test_add"] = _sample_func
        return exe

    def test_execute_event_with_kwargs(self):
        exe = self._make_executor()
        result = exe._execute_event(["test_add", {"a": 3, "b": 4}])
        assert result == 7

    def test_execute_event_with_args(self):
        exe = self._make_executor()
        result = exe._execute_event(["test_add", [10, 20]])
        assert result == 30

    def test_execute_event_no_args(self):
        exe = self._make_executor()
        result = exe._execute_event(["test_add"])
        assert result == 0

    def test_execute_event_unknown_raises(self):
        exe = self._make_executor()
        with pytest.raises(LoadDensityTestExecuteException):
            exe._execute_event(["nonexistent_command"])

    def test_execute_action_list(self):
        exe = self._make_executor()
        actions = [
            ["test_add", {"a": 1, "b": 2}],
            ["test_add", {"a": 10, "b": 20}],
        ]
        result = exe.execute_action(actions)
        values = list(result.values())
        assert values[0] == 3
        assert values[1] == 30

    def test_execute_action_dict_format(self):
        exe = self._make_executor()
        actions = {
            "load_density": [
                ["test_add", {"a": 5, "b": 5}],
            ]
        }
        result = exe.execute_action(actions)
        assert list(result.values())[0] == 10

    def test_execute_action_dict_missing_key_raises(self):
        exe = self._make_executor()
        with pytest.raises(LoadDensityTestExecuteException):
            exe.execute_action({"wrong_key": []})

    def test_execute_files(self, tmp_path):
        exe = self._make_executor()
        action_file = tmp_path / "actions.json"
        actions = [["test_add", {"a": 100, "b": 200}]]
        action_file.write_text(json.dumps(actions), encoding="utf-8")

        results = exe.execute_files([str(action_file)])
        assert len(results) == 1
        assert list(results[0].values())[0] == 300

    def test_builtin_functions_available(self):
        exe = Executor()
        assert "print" in exe.event_dict
        assert "len" in exe.event_dict

    def test_default_events_registered(self):
        exe = Executor()
        assert "LD_start_test" in exe.event_dict
        assert "LD_generate_html" in exe.event_dict
        assert "LD_generate_json" in exe.event_dict
        assert "LD_generate_xml" in exe.event_dict


class TestAddCommandToExecutor:

    def test_add_function(self):
        from je_load_density.utils.executor.action_executor import executor
        add_command_to_executor({"my_func": _sample_func})
        assert "my_func" in executor.event_dict
        assert executor.event_dict["my_func"](a=2, b=3) == 5

    def test_add_non_callable_raises(self):
        with pytest.raises(LoadDensityTestExecuteException):
            add_command_to_executor({"bad": "not_a_function"})
