from je_load_density import start_test
from je_load_density import SequentialTaskSet, task


class TestSet(SequentialTaskSet):

    @task
    def test1(self):
        print("test1")

    @task
    def test2(self):
        print("test2")

    @task
    def test3(self):
        print("test3")


start_test(
    {
        "user": "sequence_user",
    },
    50, 10, 5,
    **{"tasks": TestSet}
)
