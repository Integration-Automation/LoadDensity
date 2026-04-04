安裝
====

系統需求
--------

* Python **3.10** 或更新版本
* pip 19.3 或更新版本

支援平台
~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 平台
     - 版本
   * - Windows
     - 10 / 11
   * - macOS
     - 10.15 ~ 11 (Big Sur)
   * - Linux
     - Ubuntu 20.04
   * - Raspberry Pi
     - 3B+

基本安裝（CLI 與函式庫）
--------------------------

從 PyPI 安裝 LoadDensity：

.. code-block:: bash

    pip install je_load_density

這會安裝核心函式庫與 CLI 工具。`Locust <https://locust.io/>`_ 會作為相依套件自動安裝。

安裝 GUI 支援
--------------

若要使用可選的 PySide6 圖形化介面：

.. code-block:: bash

    pip install je_load_density[gui]

這會額外安裝：

* `PySide6 <https://doc.qt.io/qtforpython/>`_ — Qt for Python 綁定
* `qt-material <https://github.com/UN-GCPDS/qt-material>`_ — Material Design 主題

開發者安裝
----------

從原始碼安裝進行開發：

.. code-block:: bash

    git clone https://github.com/Intergration-Automation-Testing/LoadDensity.git
    cd LoadDensity
    pip install -e .
    pip install -r dev_requirements.txt

驗證安裝
--------

安裝後，驗證 LoadDensity 是否正確安裝：

.. code-block:: bash

    python -c "from je_load_density import start_test; print('LoadDensity 安裝成功')"

也可以檢查已安裝的版本：

.. code-block:: bash

    pip show je_load_density
