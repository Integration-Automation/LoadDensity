import os
import time

from load_testing_je import start_locust
from load_testing_je import stop_locust


if __name__ == "__main__":
    locust_process = start_locust(os.getcwd() + r"/test/test_source")
    time.sleep(5)
    stop_locust(locust_process)
