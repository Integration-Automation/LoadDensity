from locust import TaskSet, task


class TaskSetWrapper(TaskSet):

    @task
    def stop(self):
        self.interrupt()
