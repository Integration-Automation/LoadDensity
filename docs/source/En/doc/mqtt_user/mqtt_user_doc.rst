MQTT User
=========

Overview
--------

The MQTT user template drives ``connect`` / ``publish`` / ``subscribe``
/ ``disconnect`` against an MQTT broker. It uses ``paho-mqtt``, loaded
lazily — install with ``pip install je_load_density[mqtt]``.

Task fields
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Meaning
   * - ``method``
     - ``connect`` / ``publish`` / ``subscribe`` / ``disconnect``.
   * - ``broker`` / ``host``
     - ``host:port`` of the MQTT broker.
   * - ``topic``
     - Topic for publish / subscribe.
   * - ``payload``
     - Body for publish (``str`` or ``bytes``).
   * - ``qos``
     - 0 / 1 / 2.
   * - ``retain``
     - Boolean.
   * - ``username`` / ``password``
     - Credentials.
   * - ``client_id``
     - Optional client id (defaults to a random hex token).
   * - ``timeout``
     - Publish wait timeout (default 5 seconds).

Example
-------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "mqtt_user"},
        user_count=10,
        spawn_rate=5,
        test_time=60,
        tasks=[
            {"method": "connect", "broker": "127.0.0.1:1883"},
            {"method": "subscribe", "topic": "telemetry/in", "qos": 1},
            {"method": "publish", "topic": "telemetry/out",
             "payload": "ping", "qos": 1},
            {"method": "disconnect"},
        ],
    )

Each step fires a Locust event tagged ``MQTT``.
