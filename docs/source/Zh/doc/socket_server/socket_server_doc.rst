TCP 控制 Socket Server
======================

概觀
----

控制 socket server 是 gevent 為基礎的 TCP listener，將收到的 LoadDensity 動作 JSON 透過網路執行。硬化版協定加入 length-prefix framing、選用 TLS，以及共享密鑰 token；舊版未驗證模式仍保留以維持相容。

模式
----

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 模式
     - 註記
   * - ``legacy``
     - 單次 ``recv(8192)``、純 JSON、無驗證。預設模式以維持舊客戶端（如 PyBreeze）相容。
   * - ``framed``
     - 4-byte big-endian 長度前綴 + JSON body。對 partial read 與超大 payload 較安全（1 MiB 上限）。
   * - ``framed + TLS``
     - 以 ``ssl.create_default_context``（TLS 1.2+）包裝連線，需 cert/key 檔案。

驗證
----

傳入 ``token=``（或設定 ``LOAD_DENSITY_SOCKET_TOKEN``）即可要求共享密鑰。一旦設定：

* ``quit_server`` 沒有正確 token 將被拒絕。
* 所有指令 payload 必須使用 envelope ``{"token": "...", "command": [...action JSON...]}``，可以 ``"op": "quit"`` 表示停機。

Token 以 ``hmac.compare_digest`` 比對，避免 timing oracle。

啟動 server
-----------

Python::

    from je_load_density import start_load_density_socket_server

    start_load_density_socket_server(
        host="0.0.0.0",
        port=9940,
        framed=True,
        token="ROTATE_ME",
        certfile="/etc/loaddensity/server.crt",
        keyfile="/etc/loaddensity/server.key",
    )

CLI::

    python -m je_load_density serve \
        --host 0.0.0.0 --port 9940 --framed \
        --token "$LOAD_DENSITY_SOCKET_TOKEN"

傳送指令（framed 模式）
-----------------------

.. code-block:: python

    import json, socket, struct

    payload = json.dumps({
        "token": "ROTATE_ME",
        "command": {"load_density": [["LD_summary", {}]]}
    }).encode("utf-8")

    sock = socket.create_connection(("127.0.0.1", 9940))
    sock.sendall(struct.pack("!I", len(payload)) + payload)
    while True:
        header = sock.recv(4)
        if not header:
            break
        (length,) = struct.unpack("!I", header)
        chunk = sock.recv(length)
        if chunk == b"Return_Data_Over_JE\n":
            break
        print(chunk.decode("utf-8"))
    sock.close()

關閉
----

* Legacy 模式：傳送字面字串 ``quit_server``。
* Framed 模式（含 token）：傳送 ``{"token": "...", "op": "quit"}``。

Server 列印 ``Server shutdown complete`` 後結束。

注意事項
--------

* 啟動時會呼叫 ``gevent.monkey.patch_all()``，整合時請留意。
* token 可由環境變數 ``LOAD_DENSITY_SOCKET_TOKEN`` 讀取，避免將密鑰寫進指令參數。
