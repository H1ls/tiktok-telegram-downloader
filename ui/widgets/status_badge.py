"""Индикатор состояния, обновляемый существующими сигналами сервиса."""

from PyQt6 import QtWidgets


class StatusBadge(QtWidgets.QLabel):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setProperty("role", "badge")
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.set_running(False)

    def set_running(self, running: bool) -> None:
        self.setText("●  Running" if running else "●  Stopped")
        self.setProperty("status", "running" if running else "stopped")
        self.setAccessibleName("Bot running" if running else "Bot stopped")
        self.style().unpolish(self)
        self.style().polish(self)
        self.updateGeometry()
        self.update()
