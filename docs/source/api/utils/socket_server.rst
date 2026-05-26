Socket Server API
=================

A gevent-based TCP listener that runs LoadDensity action JSON over the
wire. The hardened protocol adds 4-byte big-endian length-prefix
framing (1 MiB cap), optional TLS, and a shared-secret token; the
legacy unauthenticated mode is preserved for downstream tools such as
PyBreeze.

start_load_density_socket_server()
----------------------------------

.. code-block:: python

    def start_load_density_socket_server(
        host: str = "localhost",
        port: int = 9940,
        framed: bool = False,
        token: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
    ) -> "TCPServer"

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 22 18 15 45

   * - Parameter
     - Type
     - Default
     - Description
   * - ``host``
     - ``str``
     - ``"localhost"``
     - Bind address.
   * - ``port``
     - ``int``
     - ``9940``
     - Bind port.
   * - ``framed``
     - ``bool``
     - ``False``
     - Enable length-prefix framing (1 MiB cap). Required for
       authenticated mode.
   * - ``token``
     - ``Optional[str]``
     - env / ``None``
     - Shared secret compared with ``hmac.compare_digest``. Also reads
       from the ``LOAD_DENSITY_SOCKET_TOKEN`` env var.
   * - ``certfile`` / ``keyfile``
     - ``Optional[str]``
     - ``None``
     - PEM cert and key on disk. Both must be set to enable TLS
       (``ssl.create_default_context``, TLS 1.2+ minimum).

**Returns:** ``TCPServer`` — running server instance.

Modes
-----

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Mode
     - Notes
   * - ``legacy``
     - Single ``recv(8192)``, raw JSON, no auth. Default to keep older
       clients working.
   * - ``framed``
     - 4-byte big-endian length prefix + JSON body. Safer against
       partial reads and oversized payloads (1 MiB cap).
   * - ``framed + token``
     - Each payload must use
       ``{"token": "...", "command": [...action JSON...]}`` and may set
       ``"op": "quit"`` to shut down.
   * - ``framed + token + TLS``
     - Adds an ``ssl.create_default_context`` wrap over the listener.

Sending commands (framed mode)
------------------------------

.. code-block:: python

    import json, socket, struct

    payload = json.dumps({
        "token": "ROTATE_ME",
        "command": {"load_density": [["LD_summary", {}]]}
    }).encode("utf-8")

    sock = socket.create_connection(("127.0.0.1", 9940))
    sock.sendall(struct.pack("!I", len(payload)) + payload)

Shutdown
--------

* Legacy mode: send the literal string ``quit_server``.
* Framed mode with token: send ``{"token": "...", "op": "quit"}``.

Notes
-----

* ``gevent.monkey.patch_all()`` is invoked on start-up.
* The token may be read from ``LOAD_DENSITY_SOCKET_TOKEN`` so CI
  secrets stay out of process arguments.
