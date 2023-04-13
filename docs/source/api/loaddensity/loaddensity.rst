LoadDensity API
----

.. code-block:: python

    def start_test(
            user_detail_dict: dict,
            user_count: int = 50, spawn_rate: int = 10, test_time: int = 60,
            web_ui_dict: dict = None,
            **kwargs
    ):
        """
        :param user_detail_dict: dict use to create user
        :param user_count: how many user we want to spawn
        :param spawn_rate: one time will spawn how many user
        :param test_time: total test run time
        :param web_ui_dict: web ui dict include host and port like {"host": "127.0.0.1", "port": 8089}
        :param kwargs: to catch unknown param
        :return: None
        """

.. code-block:: python

    def prepare_env(user_class: [User], user_count: int = 50, spawn_rate: int = 10, test_time: int = 60,
                web_ui_dict: dict = None,
                **kwargs):
        """
        :param user_class: locust user class
        :param user_count: how many user we want to spawn
        :param spawn_rate: one time will spawn how many user
        :param test_time: total test run time
        :param web_ui_dict: web ui dict include host and port like {"host": "127.0.0.1", "port": 8089}
        :param kwargs: to catch unknown param
        :return: None
        """
