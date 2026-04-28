Scenario Modes
==============

Overview
--------

Tasks for HTTP, FastHttp, and WebSocket users can be bundled into a
scenario object that controls *which* tasks run on each tick. Three
modes are supported:

* ``sequence`` — every task runs in order (default).
* ``weighted`` — one task is picked per tick, weighted by ``weight``.
* ``conditional`` — each task is gated by ``run_if`` / ``skip_if``
  predicates evaluated against the parameter resolver.

Shape
-----

.. code-block:: json

    {
      "mode": "sequence",
      "tasks": [
        {"method": "get",  "request_url": "${var.base}/products"},
        {"method": "post", "request_url": "${var.base}/cart",
         "json": {"product_id": 1}}
      ]
    }

The legacy ``{"get": {...}}`` map and a bare list also still work; the
runner normalises them to ``{"mode": "sequence", "tasks": [...]}``.

Weighted picks
--------------

Each task may carry a positive integer ``weight``; the runner picks one
task per tick with probability proportional to weight. Tasks without a
``weight`` default to 1.

.. code-block:: json

    {
      "mode": "weighted",
      "tasks": [
        {"method": "get", "request_url": "/", "weight": 3},
        {"method": "get", "request_url": "/expensive", "weight": 1}
      ]
    }

Conditional flow
----------------

``run_if`` and ``skip_if`` accept the same predicate language; ``run_if``
must be truthy for the task to run, ``skip_if`` must be falsy.

Predicates
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Form
     - Meaning
   * - ``true`` / ``false`` / int
     - Direct truthy check.
   * - ``"${var.x}"``
     - Resolve the placeholder, then truthy check.
   * - ``{"equals": [a, b]}``
     - ``a == b`` after resolution.
   * - ``{"not_equals": [a, b]}``
     - ``a != b`` after resolution.
   * - ``{"in": [needle, haystack]}``
     - ``needle in haystack``.
   * - ``{"truthy": value}``
     - Truthy check after resolution.

Example
~~~~~~~

.. code-block:: json

    {
      "mode": "sequence",
      "tasks": [
        {"method": "post", "request_url": "/login",
         "json": {"email": "${var.email}"},
         "extract": [{"var": "auth", "from": "json_path", "path": "token"}]},
        {"method": "get",  "request_url": "/profile",
         "headers": {"Authorization": "Bearer ${var.auth}"},
         "run_if": {"truthy": "${var.auth}"}},
        {"method": "post", "request_url": "/cart",
         "json": {"product_id": 1},
         "skip_if": {"equals": ["${var.tenant}", "internal"]}}
      ]
    }
