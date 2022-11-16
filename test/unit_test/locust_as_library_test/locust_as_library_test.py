from locust import HttpUser, task

from je_load_density import start_test


# start test use user Customize class


class User(HttpUser):
    host = "https://docs.locust.io"

    @task
    def my_task(self):
        self.client.get("")

    @task
    def task_404(self):
        self.client.get("/non-existing-path")


start_test(User, user_count=100, test_time=10)
