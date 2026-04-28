GUI (Graphical User Interface)
==============================

Overview
--------

LoadDensity ships an optional PySide6 graphical front-end. It carries
the form controls for kicking off a quick HTTP test, a log panel that
mirrors the framework log, and a live stats panel that polls
``test_record_instance`` once a second.

Install
-------

.. code-block:: bash

    pip install "je_load_density[gui]"

Pulls in:

* ``PySide6`` — Qt for Python bindings.
* ``qt-material`` — Material design theme.

Launch
------

.. code-block:: python

    import sys
    from PySide6.QtWidgets import QApplication
    from je_load_density.gui.main_window import LoadDensityUI

    app = QApplication(sys.argv)
    window = LoadDensityUI()
    window.show()
    sys.exit(app.exec())

Layout
------

* **Test parameter form** — URL, test duration, user count, spawn rate,
  HTTP method.
* **Start button** — Launches the load test in a background ``QThread``.
* **Live stats panel** — Total requests, current rate, average and p95
  latency, failure count. Refreshes every 1 s.
* **Log panel** — Real-time framework log feed.
* **Material Design theme** — ``dark_amber.xml`` from ``qt-material``.

Languages
---------

The GUI ships with English, Traditional Chinese, Japanese, and
Korean translations. Switch via the ``LanguageWrapper.reset_language``
helper:

.. code-block:: python

    from je_load_density.gui.language_wrapper.multi_language_wrapper import (
        language_wrapper,
    )
    language_wrapper.reset_language("Japanese")     # or Korean / Traditional_Chinese / English

Architecture
------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Component
     - Description
   * - ``LoadDensityUI``
     - ``QMainWindow`` host. Applies theme and wires the central widget.
   * - ``LoadDensityWidget``
     - Form + start button + stats panel + log panel.
   * - ``StatsPanel``
     - QTimer-driven panel reading ``test_record_instance``.
   * - ``LoadDensityGUIThread``
     - Background ``QThread`` that runs the test without blocking the UI.
   * - ``InterceptAllFilter``
     - Captures log records into a thread-safe queue.
   * - ``log_message_queue``
     - Bridges the logger and the GUI log panel.

.. note::

    On Windows the main window sets ``AppUserModelID`` via ``ctypes`` so
    the taskbar correctly identifies the application.
