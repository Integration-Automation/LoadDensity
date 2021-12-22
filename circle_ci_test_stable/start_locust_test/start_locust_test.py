import os
import time

from load_testing_je import start_locust
from load_testing_je import stop_locust
from load_testing_je import change_to_locust_file_dir


if __name__ == "__main__":
    change_to_locust_file_dir(os.getcwd() + "/circle_ci_test_stable/start_locust_test")
    locust_process = start_locust()
    time.sleep(5)
    stop_locust(locust_process)
