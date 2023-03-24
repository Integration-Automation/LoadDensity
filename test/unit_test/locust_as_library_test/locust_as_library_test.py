from locust import HttpUser, task

from je_load_density import prepare_env


# start test use user Customize class


class User(HttpUser):
    host = "https://docs.locust.io"

    @task
    def my_task(self):
        self.client.get("")

    @task
    def task_404(self):
        self.client.get("/non-existing-path")


prepare_env(User, user_count=100, test_time=10)
