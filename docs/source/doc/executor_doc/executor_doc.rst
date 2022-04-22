==================
LocustWrapper Executor Doc
==================

.. code-block:: python

    def execute_action(action_list: list):
    """
    action_list: action's list
    """

    from je_locust_wrapper import execute_action
    """
    format [
        [function, {
            user_detail_dict:{
            request_method: value (http method),
            request_url: value (test url)
            },
            "user_count": 50, (how many user will spawn)
            "spawn_rate": 10, (one time spawn user count)
            "test_time": 10 (total test time)
        }
        ]
    ]
    param: headers, result_check_dict, params ... etc
    result_check_dict: dict to check data is verify if not raise Exception
    """
    from je_locust_wrapper import execute_action

    test_list = [
        ["loading_test_with_user", {"user_detail_dict": {
            "request_method": "get",
            "request_url": "http://httpbin.org/get"
        },
            "user_count": 50, "spawn_rate": 10, "test_time": 10}
         ]
    ]

    execute_action(test_list)

.. code-block:: python

    def execute_files(execute_files_list: list):
    """
    :param execute_files_list: list include execute files path
    :return: every execute detail as list
    """