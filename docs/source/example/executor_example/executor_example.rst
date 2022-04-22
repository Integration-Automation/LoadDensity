==================
LocustWrapper Executor Example
==================

.. code-block:: python

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
