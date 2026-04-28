TCP Control Socket Server
=========================

Overview
--------

The control socket server is a gevent-based TCP listener that runs
LoadDensity action JSON sent over the wire. The hardened protocol adds
length-prefix framing, optional TLS, and a shared-secret token; the
legacy unauthenticated mode is preserved for backwards compatibility.

Modes
-----

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Mode
     - Notes
   * - ``legacy``
     - Single ``recv(8192)``, raw JSON, no auth. Default to keep older
       clients (e.g. PyBreeze) working.
   * - ``framed``
     - 4-byte big-endian length prefix + JSON body. Safer against
       partial reads and oversized payloads (1 MiB cap).
   * - ``framed + TLS``
     - Wrap the connection with ``ssl.create_default_context`` (TLS
       1.2+ minimum) using a cert/key on disk.

Auth
----

Pass ``token=`` (or set ``LOAD_DENSITY_SOCKET_TOKEN``) to require a
shared secret. Once configured:

* ``quit_server`` is rejected without a valid token.
* All command payloads must use the envelope
  ``{"token": "...", "command": [...action JSON...]}`` and may set
  ``"op": "quit"`` to signal a shutdown.

Tokens are compared with ``hmac.compare_digest`` to avoid timing
oracles.

Starting the server
-------------------

Python::

    from je_load_density import start_load_density_socket_server

    start_load_density_socket_server(
        host="0.0.0.0",
        port=9940,
        framed=True,
        token="ROTATE_ME",
        certfile="/etc/loaddensity/server.crt",
        keyfile="/etc/loaddensity/server.key",
    )

CLI::

    python -m je_load_density serve \
        --host 0.0.0.0 --port 9940 --framed \
        --token "$LOAD_DENSITY_SOCKET_TOKEN"

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
    while True:
        header = sock.recv(4)
        if not header:
            break
        (length,) = struct.unpack("!I", header)
        chunk = sock.recv(length)
        if chunk == b"Return_Data_Over_JE\n":
            break
        print(chunk.decode("utf-8"))
    sock.close()

Shutdown
--------

* Legacy mode: send the literal string ``quit_server``.
* Framed mode (with token): send
  ``{"token": "...", "op": "quit"}``.

The server prints ``Server shutdown complete`` and exits.

Notes
-----

* ``gevent.monkey.patch_all()`` is invoked on start-up. Plan
  integration accordingly.
* The token may be read from the ``LOAD_DENSITY_SOCKET_TOKEN``
  environment variable so CI secrets stay out of process arguments.
