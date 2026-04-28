WebSocket User
==============

Overview
--------

The WebSocket user template drives a connect / send / recv loop against
a configured ``ws://`` or ``wss://`` URL. It uses the
``websocket-client`` package, which is loaded lazily — install it with
``pip install je_load_density[websocket]``.

Task fields
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Meaning
   * - ``method``
     - ``connect`` / ``send`` / ``recv`` / ``sendrecv`` / ``close``.
   * - ``request_url`` / ``url``
     - WebSocket URL (required for ``connect``; reused otherwise).
   * - ``name``
     - Event name; defaults to URL or method.
   * - ``payload``
     - String / bytes to send.
   * - ``expect``
     - Substring assertion on the received frame.
   * - ``timeout``
     - Recv timeout in seconds (default 5).

Example
-------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "websocket_user"},
        user_count=10,
        spawn_rate=5,
        test_time=60,
        tasks=[
            {"method": "connect", "request_url": "wss://echo.example.com/socket"},
            {"method": "sendrecv", "payload": '{"ping": 1}', "expect": "pong"},
            {"method": "close"},
        ],
    )

Each step fires a Locust event tagged ``WS`` for stat aggregation.
