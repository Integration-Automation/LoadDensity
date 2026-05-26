Importers
=========

Overview
--------

Six importers convert real-world test artefacts into LoadDensity
action JSON or single-task dicts. All of them produce the same task
schema so the downstream `LD_start_test` payload is identical
regardless of input format.

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Source
     - LoadDensity helper
   * - HAR (browser DevTools, mitmproxy, Charles, …)
     - ``load_har`` + ``har_to_tasks`` / ``har_to_action_json``
   * - Postman v2.1 collection
     - ``load_postman_collection`` + ``postman_to_*``
   * - OpenAPI 3.x (JSON / YAML)
     - ``load_openapi`` + ``openapi_to_*``
   * - Standalone cURL command
     - ``curl_to_task``
   * - k6 script (``http.get/post/...``, ``check()``)
     - ``load_k6_script`` + ``k6_script_to_*``
   * - JMeter JMX plan
     - ``load_jmeter_jmx`` + ``jmeter_to_*``

cURL
----

.. code-block:: python

    from je_load_density import curl_to_task

    task = curl_to_task("""curl -X POST https://api/login \\
        -H 'Content-Type: application/json' \\
        -d '{"email":"u@x","password":"s"}'""")

Supported flags: ``-X / --request``, ``-H / --header``,
``-d / --data / --data-raw / --data-binary / --data-urlencode``,
``-u / --user`` (basic auth), ``-b / --cookie``,
``-k / --insecure``, ``-L / --location``, ``--compressed``.

HAR
---

.. code-block:: python

    from je_load_density import load_har, har_to_action_json

    action_json = har_to_action_json(
        load_har("recording.har"),
        user="fast_http_user",
        user_count=20, spawn_rate=10, test_time=120,
        include=[r"api\.example\.com"],
        exclude=[r"\.svg$"],
    )

Status codes from the HAR responses flow through as ``status_code``
assertions on every generated task.

Postman v2.1
------------

.. code-block:: python

    from je_load_density import (
        load_postman_collection,
        postman_to_action_json,
    )

    action_json = postman_to_action_json(
        load_postman_collection("collection.json"),
        user="fast_http_user",
        user_count=20, spawn_rate=10, test_time=120,
    )

Walks folders recursively; raw / urlencoded / formdata bodies are all
honoured; disabled headers / fields are skipped.

OpenAPI 3.x
-----------

.. code-block:: python

    from je_load_density import load_openapi, openapi_to_action_json

    action_json = openapi_to_action_json(
        load_openapi("openapi.yaml"),     # YAML needs [yaml] extra
        user="fast_http_user",
        user_count=20, spawn_rate=10, test_time=120,
    )

Each ``(path, method)`` becomes one task; ``{param}`` path segments
are rewritten to ``${var.param}`` so the caller supplies values via
``register_variables``. First 2xx status response becomes a
``status_code`` assertion.

k6
--

.. code-block:: python

    from je_load_density import load_k6_script, k6_script_to_action_json

    action_json = k6_script_to_action_json(load_k6_script("script.js"))

Pragmatic parser — matches ``http.<method>(...)`` calls and the
adjacent ``check(res, {...})``. Not a full ES module evaluator; meant
for one-shot migrations, not 1:1 round-trips.

JMeter JMX
----------

.. code-block:: python

    from je_load_density import load_jmeter_jmx, jmeter_to_action_json

    action_json = jmeter_to_action_json(load_jmeter_jmx("plan.jmx"))

Walks the XML, emits one task per ``HTTPSamplerProxy``, inherits
headers from enclosing ``HeaderManager`` elements, and converts form
``Arguments`` to either a body string or a dict.

Action JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Command
     - Summary
   * - ``LD_load_har`` / ``LD_har_to_tasks`` / ``LD_har_to_action_json``
     - HAR pipeline.
   * - ``LD_load_postman_collection`` / ``LD_postman_to_*``
     - Postman pipeline.
   * - ``LD_load_openapi`` / ``LD_openapi_to_*``
     - OpenAPI pipeline.
   * - ``LD_curl_to_task``
     - Parse one cURL command.
   * - ``LD_load_k6_script`` / ``LD_k6_script_to_*``
     - k6 script pipeline.
   * - ``LD_load_jmeter_jmx`` / ``LD_jmeter_to_*``
     - JMeter JMX pipeline.
