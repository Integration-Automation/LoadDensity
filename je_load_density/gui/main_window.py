import sys
from typing import Optional

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from je_load_density.gui.dark_style import apply_dark_style
from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.gui.main_widget import LoadDensityWidget


class LoadDensityUI(QMainWindow):
    """
    負載測試主視窗
    Load Test Main Window

    提供 GUI 介面，整合測試控制元件與樣式設定。
    Provides the main GUI window, integrating the load test widget and applying styles.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 應用程式名稱 (Application name)
        self.id = language_wrapper.language_word_dict.get("application_name")

        # 在 Windows 平台設定 AppUserModelID，讓工作列顯示正確的應用程式名稱
        # Set AppUserModelID on Windows so the taskbar shows the correct application name
        if sys.platform in ["win32", "cygwin", "msys"]:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.id)

        apply_dark_style(self)

        # 建立並設定主要控制元件 (Create and set main widget)
        self.load_density_widget = LoadDensityWidget()
        self.setCentralWidget(self.load_density_widget)
        self.setWindowTitle(self.id)
        self.resize(1200, 850)

    def closeEvent(self, event) -> None:
        """Cancel and join the child supervisor before destroying the main window."""
        if self.load_density_widget.shutdown():
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoadDensityUI()
    window.show()
    sys.exit(app.exec())
