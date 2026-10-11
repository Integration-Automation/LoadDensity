"""Required installed wheel smoke: real HTTP execution and cancellation through desktop controls."""

import os
import sys
import time

_HTTP_SERVER = """
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'gui-smoke'
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
"""


def _until(application, predicate, timeout: float = 25) -> None:
    from PySide6.QtCore import QThread

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        application.processEvents()
        if predicate():
            return
        QThread.msleep(20)
    raise RuntimeError("GUI lifecycle did not reach the expected state")


def _run(application, widget, engine: str, *, cancel: bool) -> None:
    widget.engine_combobox.setCurrentText(engine)
    widget.test_time_input.setText("30" if cancel else "1")
    widget.start_button.click()
    worker = widget.run_load_density_thread
    if widget.run_state != "running":
        raise RuntimeError("GUI did not start")
    widget.run_load_density()
    if widget.run_load_density_thread is not worker:
        raise RuntimeError("GUI accepted a duplicate run")
    if cancel:
        _until(application, lambda: widget.last_summary.get("requests", 0) > 0)
        widget.stop_button.click()
        if widget.run_state != "stopping":
            raise RuntimeError("GUI cancellation was not visible")
    _until(application, lambda: widget.run_state not in {"running", "stopping"})
    expected = "cancelled" if cancel else "completed"
    if widget.run_state != expected:
        details = widget.log_panel.toPlainText()
        raise RuntimeError(f"GUI {engine} expected {expected}, got {widget.run_state}: {details}")
    if widget.last_summary.get("requests", 0) <= 0 or not widget.results_table.rowCount():
        raise RuntimeError("GUI failed to retain actual HTTP results")
    if widget.last_summary.get("failures", 0):
        raise RuntimeError("GUI HTTP smoke recorded failed requests")
    _until(application, lambda: not worker.isRunning())
    if worker._process is None or worker._process.poll() is None:
        raise RuntimeError("GUI worker process leaked")


def run_gui_probe() -> None:
    """Fail when GUI dependencies or either engine's actual execution/cancel path is broken."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication

    from je_load_density.gui.child_process import ChildProcess
    from je_load_density.gui.main_window import LoadDensityUI

    application = QApplication.instance() or QApplication([])
    server = ChildProcess([sys.executable, "-u", "-c", _HTTP_SERVER])
    window = None
    try:
        ready = []

        def server_ready():
            ready.extend(server.read_lines())
            return bool(ready)

        _until(application, server_ready, timeout=5)
        port = int(ready[0])
        window = LoadDensityUI()
        window.show()
        application.processEvents()
        widget = window.load_density_widget
        widget.url_input.setText(f"http://127.0.0.1:{port}/")
        widget.user_count_input.setText("1")
        widget.spawn_rate_input.setText("1")
        for engine in ("Locust", "asyncio"):
            for cancel in (False, True):
                _run(application, widget, engine, cancel=cancel)
        widget.test_time_input.setText("30")
        widget.run_load_density()
        worker = widget.run_load_density_thread
        _until(application, lambda: widget.last_summary.get("requests", 0) > 0)
        window.close()
        application.processEvents()
        if worker.isRunning() or worker._process.poll() is None:
            raise RuntimeError("Closing the GUI leaked its active child")
    finally:
        if window is not None:
            window.close()
            application.processEvents()
        server.kill()
        server.wait(timeout=3)


if __name__ == "__main__":
    run_gui_probe()
