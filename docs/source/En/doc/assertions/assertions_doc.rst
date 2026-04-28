Assertions & Extractors
=======================

Overview
--------

HTTP and FastHttp tasks accept ``assertions`` and ``extract`` blocks
that run under Locust's ``catch_response``. Failed assertions mark the
request as a Locust failure and surface in every report.

Assertions
----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - ``type``
     - Behaviour
   * - ``status_code``
     - ``int(response.status_code) == int(value)``.
   * - ``contains``
     - ``str(value) in response.text``.
   * - ``not_contains``
     - ``str(value) not in response.text``.
   * - ``json_path``
     - Resolves ``response.json()`` along ``path`` (dot-separated; list
       indices supported) and compares to ``value``.
   * - ``header``
     - ``response.headers[name] == value``.

Example
~~~~~~~

.. code-block:: json

    {
      "method": "get",
      "request_url": "${var.base}/health",
      "assertions": [
        {"type": "status_code", "value": 200},
        {"type": "json_path", "path": "status", "value": "ok"},
        {"type": "header", "name": "X-Service", "value": "checkout"}
      ]
    }

Extractors
----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - ``from``
     - Source
   * - ``json_path``
     - Same dotted path syntax as the ``json_path`` assertion.
   * - ``header``
     - ``response.headers[name]``.
   * - ``status_code``
     - ``response.status_code``.

Extracted values are written into the parameter resolver under the
chosen ``var`` name; subsequent tasks reference them as ``${var.NAME}``.

.. code-block:: json

    {
      "method": "post",
      "request_url": "${var.base}/login",
      "json": {"email": "u@example.com", "password": "secret"},
      "extract": [
        {"var": "auth_token", "from": "json_path", "path": "data.token"},
        {"var": "request_id", "from": "header",    "name": "X-Request-Id"}
      ]
    }
