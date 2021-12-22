import os
import shutil
import subprocess

from load_testing_je.utils.exception.exception import LocustNotFoundException
from load_testing_je.utils.exception.exception_tag import not_found_locust_error


def change_to_locust_file_dir(path):
    os.chdir(path)


def start_locust(**kwargs):
    global process
    locust_path = shutil.which("locust")
    if locust_path is None:
        raise LocustNotFoundException(not_found_locust_error)
    process = subprocess.Popen([locust_path], **kwargs, shell=False)
    return process


def stop_locust(stop_process):
    stop_process.terminate()
