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

Master 在開始 ramp 前最多等待 60 秒，等待 ``expected_workers`` 個 worker 加入。若僅 N（N < expected）人加入，會記錄警告並照常啟動。

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
