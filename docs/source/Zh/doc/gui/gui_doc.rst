GUI（圖形化使用者介面）
======================

LoadDensity 包含一個可選的 PySide6 圖形化介面，可透過視覺化表單執行負載測試，
並即時顯示日誌。

安裝需求
--------

GUI 需要額外的相依套件。請使用以下方式安裝：

.. code-block:: bash

    pip install je_load_density[gui]

這會安裝：

* **PySide6** (6.10.0) — Qt for Python 綁定
* **qt-material** — Material Design 主題

啟動 GUI
--------

.. code-block:: python

    from je_load_density.gui.main_window import LoadDensityUI
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = LoadDensityUI()
    window.show()
    sys.exit(app.exec())

GUI 功能
--------

GUI 提供以下功能：

* **測試參數表單** — 輸入欄位包含：

  * 目標 URL
  * 測試持續時間（秒）
  * 使用者數量（模擬使用者總數）
  * 生成速率（每秒生成使用者數量）
  * HTTP 方法選擇（GET、POST、PUT、PATCH、DELETE、HEAD、OPTIONS）

* **啟動按鈕** — 在背景執行緒中啟動負載測試（不會阻塞 UI）
* **即時日誌面板** — 每 50 毫秒更新一次，即時顯示測試執行的日誌訊息
* **Material Design 主題** — 使用 qt-material 的 ``dark_amber.xml`` 主題

語言支援
--------

GUI 支援兩種語言：

* **英文**（預設）
* **繁體中文**

語言字串由 ``je_load_density/gui/language_wrapper/`` 下的 ``language_wrapper`` 模組管理。

架構
----

GUI 由以下元件組成：

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 元件
     - 說明
   * - ``LoadDensityUI``
     - 主視窗（``QMainWindow``）。套用主題並包含 widget。
   * - ``LoadDensityWidget``
     - 中央 widget，包含表單輸入、啟動按鈕和日誌面板。
   * - ``LoadDensityGUIThread``
     - 背景 ``QThread``，在不阻塞 UI 的情況下執行負載測試。
   * - ``InterceptAllFilter``
     - 日誌過濾器，將日誌訊息擷取到佇列中供 GUI 顯示。
   * - ``log_message_queue``
     - 執行緒安全的佇列，連接日誌系統與 GUI 日誌面板。

.. note::

    在 Windows 平台上，GUI 會透過 ``ctypes`` 設定 ``AppUserModelID``，
    讓工作列能正確識別應用程式。
