通知器
======

概觀
----

將 LoadDensity 執行摘要透過 incoming webhook 推送至 Slack 與
Microsoft Teams;network I/O 可由 ``poster=`` 參數注入 mock 以便測試。

Slack(Block Kit)
-----------------

.. code-block:: python

    from je_load_density import post_slack_summary

    post_slack_summary(
        webhook_url="https://hooks.slack.com/services/T000/B000/XXXX",
        title="Smoke run",
    )

預設使用當前 ``build_summary()`` 的內容(總請求、失敗、失敗率、p95
latency 四項 field)。

Teams(MessageCard)
-------------------

.. code-block:: python

    from je_load_density import post_teams_summary

    post_teams_summary(
        webhook_url="https://outlook.office.com/webhook/...",
        title="Smoke run",
    )

使用 legacy MessageCard schema,office 365 webhook 都吃。

Datadog DogStatsD
-----------------

.. code-block:: python

    from je_load_density import start_statsd_sink, stop_statsd_sink

    start_statsd_sink(host="dogstatsd", port=8125, prefix="loaddensity")
    # ... 跑 action ...
    stop_statsd_sink()

每筆請求三個封包:``requests:1|c``、``request.latency:N|ms``、
``response.size:N|h``,皆帶 ``method`` / ``name`` / ``outcome`` tag;
純 UDP,不需 SDK 相依。

Action JSON 指令
----------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 指令
     - 說明
   * - ``LD_post_slack_summary``
     - 將 Block Kit 摘要 POST 到 Slack webhook
   * - ``LD_post_teams_summary``
     - 將 MessageCard 摘要 POST 到 Teams webhook
   * - ``LD_start_statsd_sink`` / ``LD_stop_statsd_sink``
     - 啟用 / 停用 DogStatsD UDP 推送
