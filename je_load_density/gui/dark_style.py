"""Desktop contrast independent of platform styles and optional theme packages."""

import os
from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QWidget

DARK_STYLE = """
QWidget { background-color: #171c25; color: #eef2f7; font-size: 13px; }
QGroupBox { border: 1px solid #394354; border-radius: 8px; margin-top: 13px; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #ffcf70; }
QLabel { background: transparent; color: #eef2f7; }
QLineEdit, QComboBox, QTextEdit, QTableWidget {
    background-color: #232c3b; color: #eef2f7; border: 1px solid #46536a;
    border-radius: 4px; padding: 5px; selection-background-color: #466486;
}
QLineEdit:focus, QComboBox:focus { border-color: #ffcf70; }
QComboBox QAbstractItemView { background: #232c3b; color: #eef2f7; selection-background-color: #466486; }
QPushButton { background: #34445c; color: #ffffff; border: 1px solid #526781; border-radius: 5px; padding: 7px 16px; }
QPushButton:hover { background: #425a7b; }
QPushButton:pressed { background: #26364e; }
QPushButton:disabled, QWidget:disabled { color: #93a0b5; }
QHeaderView::section { background: #303c50; color: #eef2f7; border: 0; padding: 7px; }
QTableWidget { gridline-color: #3d4960; }
QTabWidget::pane { border: 1px solid #394354; }
QTabBar::tab { background: #273246; color: #cdd7e5; padding: 9px 16px; border: 1px solid #394354; }
QTabBar::tab:selected { background: #394b67; color: #ffcf70; }
QSplitter::handle { background: #394354; }
QScrollBar { background: #1b2230; }
QScrollBar::handle { background: #526781; border-radius: 4px; min-height: 20px; min-width: 20px; }
"""


@lru_cache(maxsize=1)
def _desktop_font() -> str:
    # Offscreen Qt may not scan the operating system font directories itself.
    candidates = (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf",
                  Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                  Path("/System/Library/Fonts/SFNS.ttf"))
    for path in candidates:
        if path.is_file():
            identifier = QFontDatabase.addApplicationFont(str(path))
            families = QFontDatabase.applicationFontFamilies(identifier)
            if families:
                return families[0]
    return "sans-serif"


def apply_dark_style(widget: QWidget) -> None:
    """Apply readable controls and register an OS font when using offscreen Qt."""
    family = _desktop_font()
    widget.setFont(QFont(family, 10))
    widget.setStyleSheet(DARK_STYLE + f'QWidget {{ font-family: "{family}"; }}')
