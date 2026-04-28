Locust 環境
===========

概觀
----

``prepare_env`` 與 ``create_env`` 封裝 ``locust.env.Environment``，把 wiring runner、stats printer、可選 Web UI 的樣板程式都隱藏起來。

create_env
----------

建立 ``Environment`` 與 runner，但不啟動任何 user：

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

當你需要在 runner 啟動前掛上額外事件監聽器時使用。

prepare_env
-----------

完整生命週期 helper：建立 environment → 啟動 runner → 視情況啟動 Locust Web UI → 在 ``test_time`` 後停止 → join。

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

傳入 ``web_ui_dict`` 即可啟動 Locust web UI。只有 local 與 master 模式會啟動 UI；workers 永遠不啟動。

Stats greenlets
---------------

local 與 master 模式下，``create_env`` 會 spawn Locust 標準 ``stats_printer`` 與 ``stats_history`` greenlet。Workers 兩者皆跳過，因為由 master 收集並列印。
