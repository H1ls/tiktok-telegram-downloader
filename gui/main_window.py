from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from gui.bot_control_tab import BotControlTab
from gui.settings_tab import SettingsTab
from gui.tray import Tray


class MainWindow(QtWidgets.QMainWindow):
    start_clicked = QtCore.pyqtSignal()
    stop_clicked = QtCore.pyqtSignal()
    settings_saved = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok Downloader Bot")

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        self.bot_tab = BotControlTab()
        self.settings_tab = SettingsTab()
        self.tabs.addTab(self.bot_tab, "Bot")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.bot_tab.start_clicked.connect(self.start_clicked.emit)
        self.bot_tab.stop_clicked.connect(self.stop_clicked.emit)
        self.settings_tab.settings_saved.connect(self.settings_saved.emit)

        self.tray = Tray(self)
        self.tray.tray.hide()
        self.resize(470, 560)

    def append_log(self, text: str) -> None:
        self.bot_tab.append_log(text)

    def set_running(self, running: bool) -> None:
        self.bot_tab.set_running(running)

    def closeEvent(self, event) -> None:
        if getattr(self, "_really_quit", False):
            self.tray.tray.hide()
            event.accept()
            return

        if self.bot_tab.minimize_to_tray_enabled():
            event.ignore()
            self.hide()
            if not self.tray.tray.isVisible():
                self.tray.tray.show()
            self.tray.tray.showMessage("TikTok Bot", "Application minimized to tray")
            return

        event.ignore()
        self.stop_clicked.emit()
        self.tray.tray.hide()
        QtWidgets.QApplication.quit()
