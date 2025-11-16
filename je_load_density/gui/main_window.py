import sys
from typing import Optional

from PySide6.QtWidgets import QMainWindow, QApplication, QWidget
from qt_material import QtStyleTools

from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.gui.main_widget import LoadDensityWidget


class LoadDensityUI(QMainWindow, QtStyleTools):
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

        # 設定字體樣式 (Set font style)
        self.setStyleSheet(
            "font-size: 12pt;"
            "font-family: 'Lato';"
        )

        # 套用 qt-material 樣式 (Apply qt-material theme)
        self.apply_stylesheet(self, "dark_amber.xml")

        # 建立並設定主要控制元件 (Create and set main widget)
        self.load_density_widget = LoadDensityWidget()
        self.setCentralWidget(self.load_density_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoadDensityUI()
    window.show()
    sys.exit(app.exec())