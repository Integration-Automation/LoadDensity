分散式 Master / Worker
======================

概觀
----

雲端 adapter 在聯絡 provider 前驗證 worker／資源設定。
``je_load_density.cloud.CloudLaunchError`` 保留先前接受的回應、失敗 worker 索引與失敗回應細節，
並串接 provider 例外。Fargate 拒絕部分失敗或格式錯誤的提交。Lambda 區分執行成功、Event 接受與
DryRun 驗證，保留 FunctionError payload 並關閉 payload stream。ACI 等待 provisioning，
回傳唯一 ``name``、``status="Succeeded"`` 與 ``resource_id``。
Cloud Run 每次刷新 credentials；parallelism 請設定於部署的 Job，執行覆寫支援 ``task_count``，
但拒絕 ``parallelism``。Launcher 不重試啟動，也不回滾已接受的資源。

必要契約測試使用可控 SDK double 與本機 HTTP；選用 cloud extra 測試另驗證官方 SDK serializer／stub，
不建立真實資源。接受啟動不代表 worker 已就緒或負載執行成功。

LoadDensity 透過 ``start_test`` / ``prepare_env`` 的 ``runner_mode`` 參數開放 Locust 的分散式 runner。三種模式：

* ``local`` — 單一程序（預設）。
* ``master`` — 協調 worker 群，可選擇啟動 Locust Web UI。
* ``worker`` — 加入 master 並執行指定的 user count。

Master
------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="master",
        master_bind_host="0.0.0.0",
        master_bind_port=5557,
        expected_workers=4,                # 等待 4 個 worker
        web_ui_dict={"host": "0.0.0.0", "port": 8089},
        user_count=400,
        spawn_rate=40,
        test_time=600,
        tasks=[...],
    )

Master 在 ramp 前等待健康且 ready 的 worker。設定包含 ``worker_startup_timeout``
（預設 60 秒）、``worker_heartbeat_interval``（5 秒）、``worker_lost_timeout``（15 秒）
與 ``worker_startup_policy``（``"fail"``）。人數不足時清理資源後拋出 ``TimeoutError``。
明確選擇 ``"degraded"`` 可接受不足的人數，但至少須有一個 ready worker，
即使 ``expected_workers=0`` 也適用。

每個節點須使用相同 heartbeat 設定；原生失聯偵測依 interval tick 判定。
Locust 在失聯／重連後重新分配虛擬使用者，所有 worker 失聯時終止執行。
master 結果包含 ``distributed_health``、觀測容量與受影響 ID。
有狀態流程可能重新開始；不重放請求。有限工作租約與 canonical worker record 彙整仍待實作。

``on_environment(env)`` 在執行執行緒、啟動前呼叫；``stop_requested()`` 可協作取消啟動、ramp 或執行，
callback 錯誤在清理後传回。``prepare_env`` 負責 runner／UI／RPC／輔助 task 的資源生命週期；
直接呼叫 ``create_env`` 的使用者須在完成後呼叫 ``cleanup_env(env)``。

Worker
------

於每個壓測節點執行：

.. code-block:: python

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="worker",
        master_host="10.0.0.10",
        master_port=5557,
        tasks=[...],
    )

Worker 不啟動 Web UI 並跳過本地 stats greenlet — 由 master 集中收集與發佈整體統計。

提示
----

* 在防火牆開啟 master 的 ``master_bind_port``。Locust 預設埠 ``5557``。
* 僅在 master 對 worker 可達時用 ``master_bind_host="0.0.0.0"``；否則綁定私網 IP。
* Master 與 worker 的 user 模板（``http_user`` / ``fast_http_user`` / ...）需一致 — master 廣播 user class 名稱。
* 若用 ``${csv.X.col}`` 參數化 task，每個 worker 都需註冊相同 CSV 檔（不共享狀態）。
