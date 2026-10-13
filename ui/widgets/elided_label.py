"""Однострочная подпись для длинных имён файлов и событий."""

from PyQt6 import QtCore, QtWidgets


class ElidedLabel(QtWidgets.QLabel):
    def __init__(self, text: str = "", parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._full_text = text
        self.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self.set_full_text(text)

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        self._refresh_text()

    def _refresh_text(self) -> None:
        text = self.fontMetrics().elidedText(
            self._full_text, QtCore.Qt.TextElideMode.ElideMiddle, self.contentsRect().width()
        )
        self.setText(text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_text()
