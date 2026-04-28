gRPC User
=========

Overview
--------

The gRPC user template drives unary calls against operator-supplied
stub modules. It uses ``grpcio`` (and your own ``*_pb2`` /
``*_pb2_grpc`` modules), loaded lazily — install with
``pip install je_load_density[grpc]``.

Task fields
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Meaning
   * - ``target`` / ``host``
     - gRPC endpoint, e.g. ``localhost:50051``.
   * - ``stub_path``
     - Dotted path to the stub class (``pkg.greeter_pb2_grpc.GreeterStub``).
   * - ``request_path``
     - Dotted path to the request message (``pkg.greeter_pb2.HelloRequest``).
   * - ``method``
     - Method name on the stub.
   * - ``payload``
     - Dict of fields used to construct the request message.
   * - ``metadata``
     - List of ``[key, value]`` pairs or a flat dict.
   * - ``timeout``
     - Per-call timeout in seconds (default 10).

The dotted paths are validated against a strict identifier regex
before ``importlib.import_module`` is called, so traversal-style
attacks (``../``, ``;``, ``__import__``) are rejected.

Example
-------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "grpc_user"},
        user_count=20,
        spawn_rate=5,
        test_time=60,
        tasks=[
            {
                "name": "say_hello",
                "target": "localhost:50051",
                "stub_path": "pkg.greeter_pb2_grpc.GreeterStub",
                "request_path": "pkg.greeter_pb2.HelloRequest",
                "method": "SayHello",
                "payload": {"name": "world"},
                "metadata": [["x-token", "abc"]],
                "timeout": 5,
            }
        ],
    )

Each call fires a Locust event tagged ``GRPC``.
