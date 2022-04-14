from locust import HttpUser, task
from load_testing_je import start_test


class User(HttpUser):
    host = "https://docs.locust.io"

    @task
    def my_task(self):
        self.client.get("")

    @task
    def task_404(self):
        self.client.get("/non-existing-path")


start_test(User, user_count=100)

