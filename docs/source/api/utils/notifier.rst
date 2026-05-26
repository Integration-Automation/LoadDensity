Notifier API
============

Slack
-----

.. code-block:: python

    from je_load_density import (
        build_slack_summary,
        post_slack_summary,
    )

    payload = build_slack_summary(summary, title="Smoke run")
    status  = post_slack_summary(
        webhook_url="https://hooks.slack.com/services/...",
        summary=None,        # defaults to build_summary()
        title="Smoke run",
        timeout=5.0,
        poster=None,         # optional callable for tests
    )

Payload uses Block Kit (header + section with 4 fields: requests,
failures, failure-rate, p95 latency).

Teams
-----

.. code-block:: python

    from je_load_density import (
        build_teams_summary,
        post_teams_summary,
    )

    status = post_teams_summary(
        webhook_url="https://outlook.office.com/webhook/...",
        title="Smoke run",
    )

Uses the legacy MessageCard schema (widely supported by Office 365
incoming webhooks).

Both helpers accept a ``poster`` argument:
``Callable[[str, bytes, float], int]`` returning the HTTP status. Tests
inject a fake to avoid hitting the network.

Action-JSON commands
--------------------

* ``LD_post_slack_summary``
* ``LD_post_teams_summary``
