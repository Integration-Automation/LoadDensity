架構
====

概觀
----

LoadDensity 是 Locust 之上的薄層封裝，加入 JSON 動作執行器、多協定 user 模板註冊、情境流程、資料參數化、可觀測性 sink，以及 MCP 控制介面。

依賴方向永遠是動作層 → Locust，反之不行：你的動作 JSON 描述要做什麼，executor 把每個指令對應到 Python callable，Locust 負責跑壓測。

分層
----

.. mermaid::

    flowchart TB
      cli[CLI / MCP / GUI / Socket Server] --> exec[動作 Executor]
      exec --> start[start_test]
      start --> proxy[locust_wrapper_proxy]
      proxy --> userhttp[HTTP / FastHttp]
      proxy --> userws[WebSocket]
      proxy --> usergrpc[gRPC]
      proxy --> usermqtt[MQTT]
      proxy --> usersock[Raw TCP/UDP]
      userhttp & userws & usergrpc & usermqtt & usersock --> hooks[Locust 事件]
      hooks --> records[test_record_instance]
      hooks --> exporters[Prometheus / Influx / OTel]
      records --> reports[HTML / JSON / XML / CSV / JUnit / Summary]
      records --> sqlite[SQLite 持久化]

模組對照表
----------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 模組
     - 用途
   * - ``je_load_density.utils.executor``
     - ``Executor`` 類別、dispatch table、``execute_action`` /
       ``execute_files`` 進入點。
   * - ``je_load_density.utils.parameterization``
     - ``ParameterResolver``，處理 ``${var.x}`` / ``${env.X}`` /
       ``${csv.s.col}`` / ``${faker.method}`` 與內建 helpers。
   * - ``je_load_density.utils.recording``
     - HAR 匯入 → 動作 JSON。
   * - ``je_load_density.utils.metrics``
     - Prometheus exporter、InfluxDB sink、OpenTelemetry exporter。
   * - ``je_load_density.utils.test_record``
     - 記憶體紀錄清單與選用 SQLite sink。
   * - ``je_load_density.utils.generate_report``
     - HTML / JSON / XML / CSV / JUnit / summary 產生器。
   * - ``je_load_density.utils.socket_server``
     - 含 framing、選用 TLS 與 token 的 TCP 控制平面。
   * - ``je_load_density.wrapper.proxy``
     - 各協定的 proxy，保存對應 user 模板的 task 設定。
   * - ``je_load_density.wrapper.user_template``
     - HTTP、FastHttp、WebSocket、gRPC、MQTT、raw socket 的 Locust user 類別。
   * - ``je_load_density.wrapper.start_wrapper``
     - ``start_test`` 分派器，挑選 user 模板並轉發 ``prepare_env``。
   * - ``je_load_density.wrapper.create_locust_env``
     - ``prepare_env`` / ``create_env`` 建立 local / master / worker 模式的 Locust 環境。
   * - ``je_load_density.mcp_server``
     - 提供 11 個工具的 MCP server，可讓 Claude 驅動 LoadDensity。
   * - ``je_load_density.gui``
     - 選用的 PySide6 widget（表單 + 即時統計面板）。

動作生命週期
------------

#. 呼叫端透過 CLI、MCP 工具、socket server 或直接呼叫 ``execute_action(...)`` 提交動作 JSON。
#. ``Executor.execute_action`` 對 ``event_dict`` 派發每個步驟（``LD_*`` 指令與安全的 builtin）。
#. 當步驟為 ``LD_start_test`` 時，分派器會挑選 user 模板（``http_user``、``fast_http_user``、``websocket_user``、``grpc_user``、``mqtt_user``、``socket_user``），由 ``variables`` / ``csv_sources`` 種入參數解析器後呼叫 ``prepare_env``。
#. ``prepare_env`` 以指定模式（local / master / worker）建立 Locust ``Environment`` 並啟動。
#. 每個 user 每個 tick 跑 ``run_scenario``（或對應的協定執行函式），觸發 Locust 事件並寫入 ``test_record_instance``。
#. 報告、metrics exporter、SQLite 持久化會吸收累積的紀錄。
