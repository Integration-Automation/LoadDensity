HTTP Users
==========

Overview
--------

LoadDensity ships two HTTP user templates, both wired through the same
``request_executor`` and ``scenario_runner`` modules:

* ``http_user`` — wraps ``locust.HttpUser`` (``requests`` under the
  hood).
* ``fast_http_user`` — wraps ``locust.FastHttpUser`` (geventhttpclient,
  much higher RPS).

Choose ``fast_http_user`` for high-load scenarios. Use ``http_user``
when you need ``requests``-specific features or middleware.

Task fields
-----------

Every HTTP task is a dict; the runner forwards the fields below to the
underlying client. Anything else is ignored.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Meaning
   * - ``method``
     - ``get`` / ``post`` / ``put`` / ``patch`` / ``delete`` / ``head``
       / ``options`` (case-insensitive).
   * - ``request_url`` / ``url``
     - Target URL (absolute or relative to ``host``).
   * - ``name``
     - Locust event name; defaults to the URL.
   * - ``headers``
     - Dict of request headers.
   * - ``params``
     - Query string parameters (dict or list of pairs).
   * - ``json``
     - Body serialised as JSON.
   * - ``data``
     - Form-encoded body (dict, list, or str).
   * - ``cookies``
     - Dict of cookies.
   * - ``timeout``
     - Per-request timeout in seconds.
   * - ``allow_redirects``, ``verify``, ``files``
     - Forwarded directly to the client.
   * - ``auth``
     - ``{"type": "basic", "username": "...", "password": "..."}`` or
       ``{"type": "bearer", "token": "..."}``.
   * - ``assertions``
     - Response assertions (see :doc:`../assertions/assertions_doc`).
   * - ``extract``
     - Response extractors (see :doc:`../parameter_resolver/parameter_resolver_doc`).
   * - ``weight``, ``run_if``, ``skip_if``
     - Scenario flow controls (see :doc:`../scenarios/scenarios_doc`).

Example
-------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=60,
        variables={"base": "https://api.example.com"},
        tasks=[
            {"method": "post", "request_url": "${var.base}/login",
             "json": {"email": "u@example.com", "password": "secret"},
             "extract": [
                 {"var": "auth", "from": "json_path", "path": "data.token"}
             ]},
            {"method": "get", "request_url": "${var.base}/profile",
             "headers": {"Authorization": "Bearer ${var.auth}"},
             "assertions": [{"type": "status_code", "value": 200}]},
        ],
    )
