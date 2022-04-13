from locust import HttpUser


class HttpUserWrapper(HttpUser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

