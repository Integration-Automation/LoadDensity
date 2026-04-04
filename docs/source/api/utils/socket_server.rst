Socket Server API
=================

A TCP server based on ``gevent`` for remote test execution via JSON commands.

TCPServer Class
---------------

.. code-block:: python

    class TCPServer:
        close_flag: bool
        server: socket.socket

        def socket_server(self, host: str, port: int) -> None: ...
        def handle(self, connection: socket.socket) -> None: ...

socket_server()
~~~~~~~~~~~~~~~

Start the TCP server. This is a blocking call.

**Parameters:**

* ``host`` — Server bind address
* ``port`` — Server bind port

The server listens for connections and spawns a ``gevent`` greenlet for each client.

handle()
~~~~~~~~

Handle a single client connection.

* Receives up to 8192 bytes
* Parses the received data as JSON
* Executes the actions via ``execute_action()``
* Sends results back line by line, terminated by ``Return_Data_Over_JE\n``
* Special command ``"quit_server"`` shuts down the server

start_load_density_socket_server()
----------------------------------

Convenience function to start the LoadDensity TCP server.

.. code-block:: python

    def start_load_density_socket_server(
        host: str = "localhost",
        port: int = 9940
    ) -> TCPServer

**Parameters:**

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

**Returns:** ``TCPServer`` instance.

.. note::

    This function calls ``gevent.monkey.patch_all()`` before starting the server,
    which patches standard library modules for gevent compatibility.
