import sys

from locust import HttpUser, task

# test use this user


class HelloWorldUser(HttpUser):
    @task
    def hello_world(self):
        self.client.get("http://localhost:5000")

    def on_stop(self):
        sys.exit(0)
