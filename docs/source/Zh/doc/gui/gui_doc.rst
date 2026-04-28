GUI 圖形介面
============

概觀
----

LoadDensity 內含選用的 PySide6 圖形前端。提供啟動快速 HTTP 測試的表單控制元件、鏡像框架日誌的 log panel，以及每秒輪詢 ``test_record_instance`` 的即時統計面板。

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

* **測試參數表單** — URL、測試時間、user 數、spawn rate、HTTP method。
* **開始按鈕** — 在背景 ``QThread`` 啟動壓測。
* **即時統計面板** — 總請求、目前速率、平均與 p95 延遲、失敗數。每 1 秒重新整理。
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
     - 由 QTimer 驅動、讀取 ``test_record_instance`` 的面板。
   * - ``LoadDensityGUIThread``
     - 在背景跑測試的 ``QThread``，避免阻擋 UI。
   * - ``InterceptAllFilter``
     - 將 log records 攔截至 thread-safe queue。
   * - ``log_message_queue``
     - 連接 logger 與 GUI log panel 的橋接 queue。

.. note::

    在 Windows 上，主視窗會以 ``ctypes`` 設定 ``AppUserModelID``，工作列才會顯示正確的應用名稱。
