TCP Socket 伺服器（遠端執行）
==============================

LoadDensity 內建基於 ``gevent`` 的 TCP 伺服器，可透過網路接收 JSON 指令，實現遠端測試執行。

啟動伺服器
----------

.. code-block:: python

    from je_load_density import start_load_density_socket_server

    # 啟動伺服器（阻塞呼叫）
    start_load_density_socket_server(host="localhost", port=9940)

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - 參數
     - 類型
     - 預設值
     - 說明
   * - ``host``
     - ``str``
     - ``"localhost"``
     - 伺服器綁定位址
   * - ``port``
     - ``int``
     - ``9940``
     - 伺服器綁定埠號

伺服器啟動後會輸出 ``Server started on {host}:{port}``。每個連入的連線會在獨立的
``gevent`` greenlet 中處理，支援並行請求。

從客戶端發送指令
-----------------

指令以 JSON 編碼的動作列表發送 — 與 JSON 腳本檔案使用相同的格式。

.. code-block:: python

    import socket
    import json

    # 連接到伺服器
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", 9940))

    # 發送測試指令
    command = json.dumps([
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "user_count": 10,
            "spawn_rate": 5,
            "test_time": 5,
            "tasks": {"get": {"request_url": "http://httpbin.org/get"}}
        }]
    ])
    sock.send(command.encode("utf-8"))

    # 接收回應
    response = sock.recv(8192)
    print(response.decode("utf-8"))
    sock.close()

伺服器協定
----------

* **指令格式**：JSON 編碼的動作列表（與 JSON 腳本檔案格式相同）
* **回應**：每個動作的回傳值以一行傳回，最後以 ``Return_Data_Over_JE\n`` 結尾
* **錯誤處理**：若執行過程中發生錯誤，錯誤訊息會傳回，後接 ``Return_Data_Over_JE\n``
* **緩衝區大小**：每次接收 8192 bytes

關閉伺服器
----------

發送字串 ``"quit_server"`` 即可優雅地關閉伺服器：

.. code-block:: python

    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", 9940))
    sock.send(b"quit_server")
    response = sock.recv(8192)
    print(response.decode("utf-8"))  # "Server shutting down"
    sock.close()

伺服器會關閉所有連線並輸出 ``Server shutdown complete``。

架構
----

TCP 伺服器由兩個元件組成：

* **TCPServer** — 基於 ``gevent.socket`` 的主伺服器類別。監聽連線並為每個客戶端產生 greenlet。
* **start_load_density_socket_server()** — 便利函式，呼叫
  ``gevent.monkey.patch_all()`` 並啟動伺服器。

.. note::

    啟動 socket 伺服器時會呼叫 ``gevent.monkey.patch_all()``。這會修補標準函式庫模組
    （socket、threading 等）以相容 gevent。若將 socket 伺服器整合到較大的應用程式中，
    請注意此行為。
