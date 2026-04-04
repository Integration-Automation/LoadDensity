GUI (Graphical User Interface)
==============================

LoadDensity includes an optional PySide6-based graphical interface for running load tests
with a visual form and real-time log display.

Requirements
------------

The GUI requires additional dependencies. Install with:

.. code-block:: bash

    pip install je_load_density[gui]

This installs:

* **PySide6** (6.10.0) — Qt for Python bindings
* **qt-material** — Material design theme

Launching the GUI
-----------------

.. code-block:: python

    from je_load_density.gui.main_window import LoadDensityUI
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = LoadDensityUI()
    window.show()
    sys.exit(app.exec())

GUI Features
------------

The GUI provides:

* **Test Parameter Form** — Input fields for:

  * Target URL
  * Test duration (seconds)
  * User count (number of simulated users)
  * Spawn rate (users per second)
  * HTTP method selection (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)

* **Start Button** — Launches the load test in a background thread (non-blocking UI)
* **Real-time Log Panel** — Displays log messages from the test execution in real-time,
  updated every 50ms via a QTimer
* **Material Design Theme** — Uses the ``dark_amber.xml`` theme from qt-material

Language Support
----------------

The GUI supports two languages:

* **English** (default)
* **Traditional Chinese** (繁體中文)

Language strings are managed via the ``language_wrapper`` module under
``je_load_density/gui/language_wrapper/``.

Architecture
------------

The GUI consists of the following components:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Component
     - Description
   * - ``LoadDensityUI``
     - Main window (``QMainWindow``). Applies theme and contains the widget.
   * - ``LoadDensityWidget``
     - Central widget with form inputs, start button, and log panel.
   * - ``LoadDensityGUIThread``
     - Background ``QThread`` that runs the load test without blocking the UI.
   * - ``InterceptAllFilter``
     - Log filter that captures log messages into a queue for GUI display.
   * - ``log_message_queue``
     - Thread-safe queue bridging the logger and the GUI log panel.

.. note::

    On Windows, the GUI sets ``AppUserModelID`` via ``ctypes`` so the taskbar correctly
    identifies the application.
