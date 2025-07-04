import sys

from PySide6.QtWidgets import QMainWindow, QApplication
from qt_material import QtStyleTools

from je_load_density.gui.language_wrapper.multi_language_wrapper import language_wrapper
from je_load_density.gui.main_widget import LoadDensityWidget


class LoadDensityUI(QMainWindow, QtStyleTools):

    def __init__(self):
        super().__init__()
        self.id = language_wrapper.language_word_dict.get("application_name")
        if sys.platform in ["win32", "cygwin", "msys"]:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.id)
        self.setStyleSheet(
            f"font-size: 12pt;"
            f"font-family: 'Lato';"
        )
        self.apply_stylesheet(self, "dark_amber.xml")
        self.load_density_widget = LoadDensityWidget()
        self.setCentralWidget(self.load_density_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoadDensityUI()
    window.show()
    sys.exit(app.exec())
