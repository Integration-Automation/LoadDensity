可靠度
======

概觀
----

四項可靠度控制讓 LoadDensity 能在 CI 無人值守跑而不變成「flake 工廠」:

* **自適應重試** — 指數退避 + 抖動 + per-error-class 預算;短暫抖動會
  自動回復,真正的 bug 立刻暴露。
* **失敗預算 / Circuit breaker** — 滑動視窗錯誤率;一旦回歸開始連鎖,
  整次測試會自我中止。
* **網路條件器** — per task 注入延遲 / 抖動 / 丟包,無需 kernel ``tc``
  或外部 proxy。
* **Process supervisor** — 殺死殭屍的 Locust / gevent worker,並對任意
  callable 套上硬牆鐘超時。

四者彼此獨立,任意搭配即可;皆位於
``je_load_density.utils.reliability``。

自適應重試
----------

``classify_error`` 將例外歸成三類:

* ``transient`` — 連線失敗、timeout、remote disconnect(預設預算 5)
* ``flaky`` — ``AssertionError``、``JSONDecodeError``(預設預算 2)
* ``permanent`` — 其餘(預算 0,立即丟出)

.. code-block:: python

    from je_load_density import AdaptiveRetryPolicy, run_with_retry

    policy = AdaptiveRetryPolicy(
        transient_budget=5, flaky_budget=2,
        base_delay=0.1, max_delay=2.0,
        backoff_factor=2.0, jitter=0.25,
    )
    run_with_retry(lambda: do_request(), policy=policy)

action JSON 內 per-task 宣告:

.. code-block:: json

    {"method": "post", "request_url": "${var.base}/x",
     "retry": {"transient": 3, "flaky": 1, "base_delay": 0.2}}

失敗預算
--------

.. code-block:: python

    from je_load_density import install_failure_budget

    budget = install_failure_budget(
        threshold=0.05,        # 錯誤率 > 5%
        window_seconds=30,     # ...近 30 秒內
        min_samples=50,        # ...且至少 50 筆請求
        runner_quit_callback=lambda: env.runner.quit(),
    )

被觸發後僅呼叫一次 ``runner_quit_callback``,之後的失敗會被忽略。

網路條件器
----------

per task 注入延遲 / 抖動 / 丟包;丟包以拋出 ``ConnectionError``
模擬(因此會被 retry 視為 transient)。

.. code-block:: python

    from je_load_density import install_network_conditioner

    install_network_conditioner(
        latency_ms=50, jitter_ms=20, loss_rate=0.01,
        name_filter="/checkout",   # 僅此 endpoint
    )

Process supervisor
------------------

.. code-block:: python

    from je_load_density import ProcessSupervisor, with_watchdog

    killed = ProcessSupervisor().kill_orphans()   # 需 psutil 軟相依

    result = with_watchdog(
        lambda: execute_action(action_json),
        timeout_seconds=600,
        on_timeout=lambda: print("dumping state…"),
    )

Action JSON 指令
----------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 指令
     - 說明
   * - ``LD_install_failure_budget``
     - 訂閱 Locust request 事件,加入滑動視窗失敗預算
   * - ``LD_uninstall_failure_budget``
     - 卸除 listener
   * - ``LD_install_network_conditioner``
     - 設定全域延遲 / 抖動 / 丟包注入
   * - ``LD_uninstall_network_conditioner``
     - 卸除注入
