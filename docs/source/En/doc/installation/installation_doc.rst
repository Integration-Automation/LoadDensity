Installation
============

Requirements
------------

* Python **3.10** or later
* pip 19.3 or later

Supported Platforms
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Platform
     - Notes
   * - Windows 10 / 11
     - Fully supported
   * - macOS
     - Fully supported
   * - Ubuntu / Linux
     - Fully supported
   * - Raspberry Pi
     - Tested on 3B+ and later

Base install (CLI & library)
----------------------------

.. code-block:: bash

    pip install je_load_density

This pulls in `Locust <https://locust.io/>`_ and ``defusedxml`` —
nothing else.

Optional extras
---------------

LoadDensity ships every protocol driver, exporter, recorder, and
control surface as an opt-in extra. The base package never imports
these modules eagerly, so the runtime footprint is unchanged for users
who only need HTTP load testing.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Extra
     - Adds
   * - ``gui``
     - PySide6 + qt-material (graphical front-end).
   * - ``websocket``
     - ``websocket-client`` (WebSocket user template).
   * - ``grpc``
     - ``grpcio`` + ``protobuf`` (gRPC user template).
   * - ``mqtt``
     - ``paho-mqtt`` (MQTT user template).
   * - ``prometheus``
     - ``prometheus-client`` (Prometheus exporter).
   * - ``opentelemetry``
     - OpenTelemetry SDK + OTLP gRPC exporter.
   * - ``metrics``
     - ``prometheus`` + ``opentelemetry`` bundle.
   * - ``faker``
     - ``Faker`` (powers ``${faker.method}`` placeholders).
   * - ``mcp``
     - ``mcp`` SDK (drives the MCP server for Claude).
   * - ``all``
     - Everything above.

Examples::

    pip install "je_load_density[gui]"
    pip install "je_load_density[mqtt,grpc,websocket]"
    pip install "je_load_density[metrics]"
    pip install "je_load_density[mcp]"
    pip install "je_load_density[all]"

Development install
-------------------

.. code-block:: bash

    git clone https://github.com/Integration-Automation/LoadDensity.git
    cd LoadDensity
    pip install -e ".[all]"
    pip install -r requirements.txt

Verify
------

.. code-block:: bash

    python -c "from je_load_density import start_test; print('LoadDensity installed')"
    pip show je_load_density
