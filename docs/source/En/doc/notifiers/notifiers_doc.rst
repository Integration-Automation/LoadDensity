Notifiers
=========

Overview
--------

Post LoadDensity run summaries to Slack and Microsoft Teams over their
incoming-webhook URLs. Network I/O is pluggable so tests can inject a
fake poster.

Slack (Block Kit)
-----------------

.. code-block:: python

    from je_load_density import post_slack_summary

    post_slack_summary(
        webhook_url="https://hooks.slack.com/services/T000/B000/XXXX",
        title="Smoke run",
    )

The payload is a Block Kit message — header + 4-field section
(requests, failures, failure rate, p95 latency). ``post_slack_summary``
defaults to the current ``build_summary()`` if no summary is passed.

Teams (MessageCard)
-------------------

.. code-block:: python

    from je_load_density import post_teams_summary

    post_teams_summary(
        webhook_url="https://outlook.office.com/webhook/...",
        title="Smoke run",
    )

Uses the legacy MessageCard schema (widely supported by Office 365
webhooks).

Datadog DogStatsD
-----------------

.. code-block:: python

    from je_load_density import start_statsd_sink, stop_statsd_sink

    start_statsd_sink(host="dogstatsd", port=8125, prefix="loaddensity")
    # … run actions …
    stop_statsd_sink()

Three packets per request: ``requests:1|c``, ``request.latency:N|ms``,
``response.size:N|h``, all tagged with ``method`` / ``name`` /
``outcome``. Pure UDP, no SDK dependency.

Action JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Summary
   * - ``LD_post_slack_summary``
     - POST a Block Kit summary to a Slack webhook.
   * - ``LD_post_teams_summary``
     - POST a MessageCard summary to a Teams webhook.
   * - ``LD_start_statsd_sink`` / ``LD_stop_statsd_sink``
     - Toggle the DogStatsD UDP listener.
