GUI 圖形介面
============

概觀
----

LoadDensity 提供選用的 PySide6 圖形前端。左側設定目標／動作檔、
Locust／asyncio 引擎與負載，右側顯示執行狀態、Start／Stop、指標、
圖表與最近請求。每次執行使用獨立直譯器，Qt 主行程不載入 Locust。
動作檔保留負載參數與報告動作。

Stop 先合作式取消，三秒後仍未停止則終止子行程；關閉執行中的視窗
會停止子行程並等待 QThread。完成／失敗結果保留，最近請求最多
200 筆已清理資料，日誌最多 500 段，既有持久化歷史仍可查閱。
訊息限制為 128 KiB，必要時減少請求列數。圖表接收最多 120 個以完整
子行程紀錄計算的時間窗，不受最近請求清單長度影響。

安裝
----

.. code-block:: bash

    pip install "je_load_density[gui]"

引入：

* ``PySide6`` — Qt for Python bindings。
* ``qt-material`` — Material design 主題。

啟動
----

.. code-block:: python

    import sys
    from PySide6.QtWidgets import QApplication
    from je_load_density.gui.main_window import LoadDensityUI

    app = QApplication(sys.argv)
    window = LoadDensityUI()
    window.show()
    sys.exit(app.exec())

版面
----

* **測試參數表單** — 目標／動作檔、引擎、測試時間、user 數、spawn rate、HTTP method。
* **Start／Stop** — 由背景 ``QThread`` 管理子行程的啟動與取消。
* **即時統計面板** — 從子行程快照顯示總請求、速率、平均／p95 延遲及失敗數。
* **Log panel** — 即時框架日誌。
* **Material Design 主題** — ``qt-material`` 的 ``dark_amber.xml``。

語言
----

GUI 內含英文、繁體中文、日文、韓文翻譯。透過 ``LanguageWrapper.reset_language`` 切換：

.. code-block:: python

    from je_load_density.gui.language_wrapper.multi_language_wrapper import (
        language_wrapper,
    )
    language_wrapper.reset_language("Japanese")     # 或 Korean / Traditional_Chinese / English

架構
----

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 元件
     - 說明
   * - ``LoadDensityUI``
     - ``QMainWindow`` 主機。套用主題並嵌入中央 widget。
   * - ``LoadDensityWidget``
     - 表單 + 開始按鈕 + 統計面板 + log panel。
   * - ``StatsPanel``
     - 透過 GUI thread signal 接收累積執行快照。
   * - ``LoadDensityGUIThread``
     - 管理獨立直譯器及有界 JSON 訊息的背景 ``QThread``。
   * - ``InterceptAllFilter``
     - 將 log records 攔截至 thread-safe queue。
   * - ``log_message_queue``
     - 連接 logger 與 GUI log panel 的橋接 queue。

.. note::

    在 Windows 上，主視窗會以 ``ctypes`` 設定 ``AppUserModelID``，工作列才會顯示正確的應用名稱。
