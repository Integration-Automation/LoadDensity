Installation
============

Requirements
------------

* Python **3.10** or later
* pip 19.3 or later

Supported Platforms
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Platform
     - Version
   * - Windows
     - 10 / 11
   * - macOS
     - 10.15 ~ 11 (Big Sur)
   * - Linux
     - Ubuntu 20.04
   * - Raspberry Pi
     - 3B+

Basic Installation (CLI & Library)
----------------------------------

Install LoadDensity from PyPI:

.. code-block:: bash

    pip install je_load_density

This installs the core library and CLI. `Locust <https://locust.io/>`_ is automatically
installed as a dependency.

Installation with GUI Support
-----------------------------

To use the optional PySide6-based graphical interface:

.. code-block:: bash

    pip install je_load_density[gui]

This additionally installs:

* `PySide6 <https://doc.qt.io/qtforpython/>`_ — Qt for Python bindings
* `qt-material <https://github.com/UN-GCPDS/qt-material>`_ — Material design theme

Development Installation
-------------------------

To install from source for development:

.. code-block:: bash

    git clone https://github.com/Intergration-Automation-Testing/LoadDensity.git
    cd LoadDensity
    pip install -e .
    pip install -r dev_requirements.txt

Verify Installation
-------------------

After installation, verify that LoadDensity is correctly installed:

.. code-block:: bash

    python -c "from je_load_density import start_test; print('LoadDensity installed successfully')"

You can also check the installed version:

.. code-block:: bash

    pip show je_load_density
