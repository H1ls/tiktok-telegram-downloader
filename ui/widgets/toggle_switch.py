"""Переключатель с нативными Qt-сигналами и управлением с клавиатуры."""

from PyQt6 import QtCore, QtGui, QtWidgets


class ToggleSwitch(QtWidgets.QAbstractButton):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(48, 28)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self.update)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        color = "#2DA8FF" if self.isChecked() else "#25344D"
        if self.underMouse():
            color = "#39B4FF" if self.isChecked() else "#344967"
        if self.isDown():
            color = "#187ABE" if self.isChecked() else "#182842"
        if not self.isEnabled():
            color = "#142137"
        outline = "#F5F7FB" if self.hasFocus() and self.isEnabled() else color
        painter.setPen(QtGui.QPen(QtGui.QColor(outline), 1))
        painter.setBrush(QtGui.QColor(color))
        painter.drawRoundedRect(QtCore.QRectF(1, 1, 46, 26), 13, 13)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor("#F5F7FB" if self.isEnabled() else "#687A96"))
        painter.drawEllipse(QtCore.QRectF(23 if self.isChecked() else 3, 4, 20, 20))
