"""Native engine entry points preserve the interpreter's I/O scheduling."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize("name", ["task", "TaskSet", "SequentialTaskSet"])
def test_selecting_locust_exports_registers_legacy_request_records(name):
    source = (
        "from je_load_density import "
        + name
        + """, test_record_instance
from locust import events
events.request.fire(start_time=100, url='http://local', request_type='GET', name='one',
                    context={}, response=None, exception=None, response_length=0, response_time=1)
assert len(test_record_instance.test_record_list) == 1
"""
    )
    result = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "statement",
    [
        "import je_load_density",
        "from je_load_density import run_async_load, build_summary, start_test",
        "from je_load_density.engine.asyncio_engine import run_async_load",
        "from je_load_density.wrapper.start_wrapper.start_test import start_test",
        "from je_load_density import execute_action; execute_action({'load_density': [['LD_summary']]})",
        "from je_load_density.__main__ import _build_parser; _build_parser()",
    ],
)
def test_native_entry_points_do_not_import_locust_or_patch_io(statement):
    source = (
        """
import socket, ssl, threading, time, sys
original = (socket.socket, ssl.SSLSocket, threading.Thread, time.sleep)
"""
        + statement
        + """
assert 'locust' not in sys.modules, 'native import eagerly loads Locust'
assert 'gevent.monkey' not in sys.modules, 'native import loads gevent monkey patching'
assert original == (socket.socket, ssl.SSLSocket, threading.Thread, time.sleep)
"""
    )
    result = subprocess.run([sys.executable, "-c", source], text=True, capture_output=True, timeout=20, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_package_inspection_does_not_register_unrestricted_import_helper():
    source = """
from je_load_density.utils.exception.exceptions import LoadDensityTestExecuteException
from je_load_density.utils.executor.action_executor import Executor
from je_load_density.utils.package_manager.package_manager_class import PackageManager
manager = PackageManager()
manager.executor = Executor()
manager.set_allow_arbitrary_packages(False)
manager.allow_packages('je_load_density')
manager.add_package_to_executor('je_load_density')
assert callable(manager.executor.event_dict['resolve'])
try:
    manager.add_package_to_executor('os')
except LoadDensityTestExecuteException:
    pass
else:
    raise AssertionError('host package gate did not refuse os')
assert 'import_module' not in manager.executor.event_dict, 'public inspection registered an unrestricted module loader'
"""
    result = subprocess.run([sys.executable, "-c", source], text=True, capture_output=True, timeout=20, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
