"""Загрузка общей темы и ресурсов из исходников и PyInstaller bundle."""

from pathlib import Path
import sys

from PyQt6 import QtGui, QtWidgets


SPACING = (4, 8, 12, 16, 20, 24, 32)
PAGE_MARGIN = 24
CARD_PADDING = 20
COMPACT_CARD_PADDING = 16
CARD_GAP = 16
CONTROL_GAP = 8


def resource_path(relative: str) -> Path:
    root = Path(sys._MEIPASS) / "ui" if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return root / relative


def icon(name: str) -> QtGui.QIcon:
    return QtGui.QIcon(str(resource_path(f"icons/{name}.svg")))


def apply_theme(app: QtWidgets.QApplication) -> None:
    app.setStyle("Fusion")
    families = set(QtGui.QFontDatabase.families())
    candidates = ("Segoe UI Variable", "Segoe UI", "Arial")
    family = next((name for name in candidates if name in families), app.font().family())
    font = QtGui.QFont(family)
    font.setPixelSize(14)
    app.setFont(font)
    palette = QtGui.QPalette()
    for role, color in (
        (QtGui.QPalette.ColorRole.Window, "#08111F"),
        (QtGui.QPalette.ColorRole.WindowText, "#F5F7FB"),
        (QtGui.QPalette.ColorRole.Base, "#0B1422"),
        (QtGui.QPalette.ColorRole.AlternateBase, "#142137"),
        (QtGui.QPalette.ColorRole.Text, "#F5F7FB"),
        (QtGui.QPalette.ColorRole.Button, "#142137"),
        (QtGui.QPalette.ColorRole.ButtonText, "#F5F7FB"),
        (QtGui.QPalette.ColorRole.Highlight, "#2DA8FF"),
        (QtGui.QPalette.ColorRole.HighlightedText, "#08111F"),
        (QtGui.QPalette.ColorRole.ToolTipBase, "#142137"),
        (QtGui.QPalette.ColorRole.ToolTipText, "#F5F7FB"),
    ):
        palette.setColor(role, QtGui.QColor(color))
    disabled_roles = (
        QtGui.QPalette.ColorRole.Text,
        QtGui.QPalette.ColorRole.WindowText,
        QtGui.QPalette.ColorRole.ButtonText,
    )
    for role in disabled_roles:
        palette.setColor(QtGui.QPalette.ColorGroup.Disabled, role, QtGui.QColor("#687A96"))
    app.setPalette(palette)
    qss = resource_path("styles/dark_theme.qss").read_text(encoding="utf-8")
    qss = qss.replace("__CHECK_ICON__", resource_path("icons/check.svg").as_posix())
    app.setStyleSheet(qss)
