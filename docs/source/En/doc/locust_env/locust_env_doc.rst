Locust Environment
==================

Overview
--------

``prepare_env`` and ``create_env`` wrap ``locust.env.Environment`` and
hide the boilerplate of wiring up runners, stats printers, and the
optional Web UI.

create_env
----------

Builds an ``Environment`` and a runner without starting any users:

.. code-block:: python

    from je_load_density import create_env
    from je_load_density.wrapper.user_template.fast_http_user_template import (
        FastHttpUserWrapper,
    )

    env = create_env(
        FastHttpUserWrapper,
        runner_mode="local",          # "local" | "master" | "worker"
        master_bind_host="*",
        master_bind_port=5557,
        master_host="127.0.0.1",
        master_port=5557,
    )

Use ``create_env`` when you want to attach extra event listeners
before the runner is started.

prepare_env
-----------

A complete lifecycle helper: create environment → start runner →
optionally launch the Locust Web UI → schedule a stop after
``test_time`` → join.

.. code-block:: python

    from je_load_density import prepare_env

    prepare_env(
        user_class=FastHttpUserWrapper,
        user_count=50,
        spawn_rate=10,
        test_time=60,
        web_ui_dict={"host": "127.0.0.1", "port": 8089},
    )

Web UI
------

Pass ``web_ui_dict`` to ``prepare_env`` (or to ``start_test``) to enable
the Locust web UI on the configured host/port. The UI is only started
in local and master modes; workers never start a UI.

Stats greenlets
---------------

In local and master modes, ``create_env`` spawns the standard Locust
``stats_printer`` and ``stats_history`` greenlets so the console keeps
streaming aggregate stats and the in-memory history is updated for
charting. Workers skip both because the master collects and prints.
