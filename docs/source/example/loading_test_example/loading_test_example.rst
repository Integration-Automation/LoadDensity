====================================
LoadDensity Loading Test Example
====================================

.. code-block:: python

    """
    http method: get
    url: http://httpbin.org/get
    total user: 50
    one time spawn user: 10
    total test_time: 10
    """
    loading_test_with_user(
        {
            "request_method": "get",
            "request_url": "http://httpbin.org/get"
        },
        user_count=50, spawn_rate=10, test_time=10
    )

