from locust import HttpUser, task, between
from load_testing_je import create_env
from load_testing_je import start_test


class User(HttpUser):
    wait_time = between(1, 3)
    host = "https://docs.locust.io"

    @task
    def my_task(self):
        self.client.get("/")

    @task
    def task_404(self):
        self.client.get("/non-existing-path")


start_test(create_env(User), test_time=5)

