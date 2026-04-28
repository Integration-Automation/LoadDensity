HAR Record / Replay
===================

Overview
--------

The HAR importer turns recorded HTTP traffic (HAR JSON) into a list of
LoadDensity tasks or a complete runnable action JSON. Capture HAR via
Chrome / Firefox DevTools, mitmproxy, Charles, or any tool that
exports the `HAR 1.2 <https://www.softwareishard.com/blog/har-12-spec/>`_
format.

Python API
----------

.. code-block:: python

    from je_load_density import load_har, har_to_tasks, har_to_action_json

    har = load_har("recording.har")
    tasks = har_to_tasks(har, include=[r"example\.com"], exclude=[r"\.svg$"])
    action_json = har_to_action_json(
        har,
        user="fast_http_user",
        user_count=20,
        spawn_rate=10,
        test_time=120,
        include=[r"api\.example\.com"],
    )

Filters
-------

* ``include`` — list of regex patterns; an entry is kept only if its
  URL matches any pattern.
* ``exclude`` — list of regex patterns; an entry is dropped if its URL
  matches any pattern.

Mapping rules
-------------

* HTTP method, URL, and request headers are copied directly.
* Hop-by-hop and HTTP/2 pseudo headers
  (``host``, ``content-length``, ``connection``, ``:authority``, …)
  are stripped.
* JSON request bodies (``application/json`` MIME) are parsed into the
  ``json`` field; form params become ``data`` dicts; raw text bodies
  fall back to ``data`` strings.
* The captured response status becomes a ``status_code`` assertion on
  the generated task.

Action JSON
-----------

.. code-block:: json

    {"load_density": [
      ["LD_har_to_action_json", {
        "har": {"log": {...}},
        "user": "fast_http_user",
        "user_count": 20,
        "spawn_rate": 10,
        "test_time": 120
      }]
    ]}

The result of ``LD_har_to_action_json`` is itself an action JSON that
can be saved or piped into ``LD_execute_action``.
