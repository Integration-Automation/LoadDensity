HAR Recording API
=================

The recording layer converts real browser traffic (HAR files captured
from Chrome / Firefox DevTools, mitmproxy, Charles, …) into a runnable
LoadDensity action JSON.

load_har()
----------

.. code-block:: python

    from je_load_density import load_har

    har = load_har("recording.har")

Reads and parses a HAR JSON document from disk. Returns a Python dict
matching the HAR 1.2 schema.

har_to_tasks()
--------------

.. code-block:: python

    from je_load_density import har_to_tasks

    tasks = har_to_tasks(
        har,
        include=[r"api\.example\.com"],
        exclude=[r"\.svg$"],
    )

Converts a HAR document into a list of LoadDensity HTTP task dicts.
Each generated task carries the original status code as a
``status_code`` assertion so a replay can be gated by the recorded
behaviour.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Parameter
     - Description
   * - ``har``
     - HAR dict (e.g. from ``load_har``).
   * - ``include``
     - List of regex patterns; only matching URLs are kept.
   * - ``exclude``
     - List of regex patterns; matching URLs are dropped.

har_to_action_json()
--------------------

.. code-block:: python

    from je_load_density import har_to_action_json

    action_json = har_to_action_json(
        har,
        user="fast_http_user",
        user_count=20, spawn_rate=10, test_time=120,
        include=[r"api\.example\.com"],
        exclude=[r"\.svg$"],
    )

Wraps ``har_to_tasks`` in an ``LD_start_test`` action so the result
can be fed directly to ``execute_action`` / the CLI / the MCP server.

Other importers
---------------

The same module ships parallel pipelines for Postman v2.1
collections, OpenAPI 3.x specs, standalone cURL commands, k6 scripts,
and JMeter JMX plans. They all return an ``LD_start_test`` action
with a ``"sequence"`` task list.

.. code-block:: python

    from je_load_density import (
        load_postman_collection, postman_to_action_json,
        load_openapi, openapi_to_action_json,
        curl_to_task,
        load_k6_script, k6_script_to_action_json,
        load_jmeter_jmx, jmeter_to_action_json,
    )

OpenAPI rewrites ``{param}`` path segments to ``${var.param}``; k6
parses ``http.<method>`` calls plus the adjacent ``check()`` for a
``status_code`` assertion; JMeter walks the JMX tree and inherits
headers from enclosing ``HeaderManager`` siblings.

Action-JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Command
     - Summary
   * - ``LD_load_har`` / ``LD_har_to_tasks`` / ``LD_har_to_action_json``
     - HAR pipeline.
   * - ``LD_load_postman_collection`` / ``LD_postman_to_*``
     - Postman v2.1 pipeline.
   * - ``LD_load_openapi`` / ``LD_openapi_to_*``
     - OpenAPI 3.x pipeline.
   * - ``LD_curl_to_task``
     - Parse one cURL command into a task dict.
   * - ``LD_load_k6_script`` / ``LD_k6_script_to_*``
     - k6 script pipeline.
   * - ``LD_load_jmeter_jmx`` / ``LD_jmeter_to_*``
     - JMeter JMX pipeline.
