# gui/tray.py
from PyQt6 import QtWidgets


class Tray:
    def __init__(self, window: QtWidgets.QMainWindow):
        self.window = window
        self._really_quit = False

        icon = window.windowIcon()
        if icon.isNull():
            icon = window.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)

        self.tray = QtWidgets.QSystemTrayIcon(icon, window)

        menu = QtWidgets.QMenu()
        act_show = menu.addAction("Показать")
        act_hide = menu.addAction("Свернуть")
        menu.addSeparator()
        act_exit = menu.addAction("Выход")

        act_show.triggered.connect(self._show)
        act_hide.triggered.connect(self._hide)
        act_exit.triggered.connect(self._exit)


        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)

        self.tray.setToolTip("TikTok Bot")
        self.tray.show()  # важно

    def _exit(self):
        try:
            self.window._really_quit = True
            self.window.stop_clicked.emit()
        except Exception:
            pass
        try:
            self.tray.hide()
        except Exception:
            pass
        QtWidgets.QApplication.quit()

    def _show(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _hide(self):
        self.window.hide()

    def _on_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            if self.window.isVisible():
                self.window.hide()
            else:
                self._show()
