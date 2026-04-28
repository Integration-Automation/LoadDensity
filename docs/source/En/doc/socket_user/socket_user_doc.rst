Raw TCP / UDP User
==================

Overview
--------

The raw socket user template sends arbitrary bytes over TCP or UDP and
optionally reads back a bounded response. It uses Python's stdlib
``socket`` module, so no extra dependency is required.

Task fields
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Meaning
   * - ``protocol``
     - ``tcp`` or ``udp``.
   * - ``target`` / ``host``
     - ``host:port``.
   * - ``payload``
     - Bytes to send. Strings are encoded as UTF-8. Use a
       ``hex:DEADBEEF`` prefix to send raw bytes from a hex string.
   * - ``expect_bytes``
     - Read at most N bytes from the response (0 to skip read).
   * - ``expect_substring``
     - Substring assertion on the decoded response.
   * - ``timeout``
     - Connect / read timeout in seconds (default 5).
   * - ``name``
     - Event name; defaults to ``protocol:target``.

Example
-------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "socket_user"},
        user_count=20,
        spawn_rate=5,
        test_time=60,
        tasks=[
            {"protocol": "tcp", "target": "127.0.0.1:9000",
             "payload": "PING\\n", "expect_bytes": 64,
             "expect_substring": "PONG"},
            {"protocol": "udp", "target": "127.0.0.1:9000",
             "payload": "hex:DEADBEEF", "expect_bytes": 4},
        ],
    )

Each step fires a Locust event tagged ``TCP`` or ``UDP``.
