TCP Socket Server (Remote Execution)
=====================================

LoadDensity includes a TCP server based on ``gevent`` that accepts JSON commands over the
network, enabling remote test execution.

Starting the Server
-------------------

.. code-block:: python

    from je_load_density import start_load_density_socket_server

    # Start server (blocking call)
    start_load_density_socket_server(host="localhost", port=9940)

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Default
     - Description
   * - ``host``
     - ``str``
     - ``"localhost"``
     - Server bind address
   * - ``port``
     - ``int``
     - ``9940``
     - Server bind port

The server starts listening and prints ``Server started on {host}:{port}``. Each incoming
connection is handled in a separate ``gevent`` greenlet for concurrent request handling.

Sending Commands from a Client
-------------------------------

Commands are sent as JSON-encoded action lists — the same format used in JSON script files.

.. code-block:: python

    import socket
    import json

    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", 9940))

    # Send a test command
    command = json.dumps([
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "user_count": 10,
            "spawn_rate": 5,
            "test_time": 5,
            "tasks": {"get": {"request_url": "http://httpbin.org/get"}}
        }]
    ])
    sock.send(command.encode("utf-8"))

    # Receive response
    response = sock.recv(8192)
    print(response.decode("utf-8"))
    sock.close()

Server Protocol
---------------

* **Command format**: JSON-encoded action list (same format as JSON script files)
* **Response**: Each action's return value is sent back as a line, terminated by
  ``Return_Data_Over_JE\n``
* **Error handling**: If an error occurs during execution, the error message is sent back
  followed by ``Return_Data_Over_JE\n``
* **Buffer size**: 8192 bytes per receive

Shutting Down the Server
------------------------

Send the string ``"quit_server"`` to gracefully shut down the server:

.. code-block:: python

    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", 9940))
    sock.send(b"quit_server")
    response = sock.recv(8192)
    print(response.decode("utf-8"))  # "Server shutting down"
    sock.close()

The server will close all connections and print ``Server shutdown complete``.

Architecture
------------

The TCP server consists of two components:

* **TCPServer** — Main server class based on ``gevent.socket``. Listens for connections
  and spawns greenlets for each client.
* **start_load_density_socket_server()** — Convenience function that patches the process
  with ``gevent.monkey.patch_all()`` and starts the server.

.. note::

    ``gevent.monkey.patch_all()`` is called when starting the socket server. This patches
    standard library modules (socket, threading, etc.) to be gevent-compatible. Be aware
    of this if integrating the socket server into a larger application.
