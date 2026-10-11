GUI (Graphical User Interface)
==============================

Overview
--------

LoadDensity ships an optional PySide6 graphical front-end. It carries
settings on the left and state, Start/Stop, metrics, charts and recent requests
on the right. Choose a target or action file, Locust/asyncio engine and load
controls. Each run uses a fresh interpreter; the Qt parent never imports Locust.
Action files retain their workload and report actions.

Stop requests cooperative cancellation and escalates after three seconds.
Closing an active window stops the child and joins its QThread. Results remain
visible after completion/failure. Recent requests retain at most 200 sanitized rows,
logs retain 500 blocks and existing persisted history remains available.
The 128 KiB frame limit may retain fewer request rows. Charts receive up to 120
windows computed from complete child records, independently of the request tail.

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

* **Test parameter form** — Target/action file, engine, duration, users, spawn rate and HTTP method.
* **Start/Stop** — Launch or cancel a child supervised by a background ``QThread``.
* **Live stats panel** — Total requests, current rate, average and p95
  latency, failure count, from child snapshots.
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
     - Receives cumulative run snapshots through GUI-thread signals.
   * - ``LoadDensityGUIThread``
     - Background ``QThread`` supervising an isolated interpreter and bounded JSON frames.
   * - ``InterceptAllFilter``
     - Captures log records into a thread-safe queue.
   * - ``log_message_queue``
     - Bridges the logger and the GUI log panel.

.. note::

    On Windows the main window sets ``AppUserModelID`` via ``ctypes`` so
    the taskbar correctly identifies the application.
