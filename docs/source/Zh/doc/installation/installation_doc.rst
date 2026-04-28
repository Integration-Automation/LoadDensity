安裝
====

需求
----

* Python **3.10** 以上
* pip 19.3 以上

支援平台
~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 平台
     - 註記
   * - Windows 10 / 11
     - 完整支援
   * - macOS
     - 完整支援
   * - Ubuntu / Linux
     - 完整支援
   * - Raspberry Pi
     - 已測 3B+ 以上

基本安裝（CLI 與函式庫）
------------------------

.. code-block:: bash

    pip install je_load_density

僅引入 `Locust <https://locust.io/>`_ 與 ``defusedxml`` — 其餘皆為選用。

選用 extras
-----------

LoadDensity 將每個協定驅動、exporter、錄製器與控制介面都拆成可選 extras。基礎套件不會 eager import 這些模組，僅做 HTTP 壓測者執行期不受影響。

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Extra
     - 加入
   * - ``gui``
     - PySide6 + qt-material（圖形介面）。
   * - ``websocket``
     - ``websocket-client``（WebSocket user 模板）。
   * - ``grpc``
     - ``grpcio`` + ``protobuf``（gRPC user 模板）。
   * - ``mqtt``
     - ``paho-mqtt``（MQTT user 模板）。
   * - ``prometheus``
     - ``prometheus-client``（Prometheus exporter）。
   * - ``opentelemetry``
     - OpenTelemetry SDK + OTLP gRPC exporter。
   * - ``metrics``
     - 結合 ``prometheus`` 與 ``opentelemetry``。
   * - ``faker``
     - ``Faker``（驅動 ``${faker.method}`` 占位符）。
   * - ``mcp``
     - ``mcp`` SDK（驅動 Claude 用的 MCP server）。
   * - ``all``
     - 上述全部。

範例::

    pip install "je_load_density[gui]"
    pip install "je_load_density[mqtt,grpc,websocket]"
    pip install "je_load_density[metrics]"
    pip install "je_load_density[mcp]"
    pip install "je_load_density[all]"

開發安裝
--------

.. code-block:: bash

    git clone https://github.com/Integration-Automation/LoadDensity.git
    cd LoadDensity
    pip install -e ".[all]"
    pip install -r requirements.txt

驗證
----

.. code-block:: bash

    python -c "from je_load_density import start_test; print('LoadDensity installed')"
    pip show je_load_density
