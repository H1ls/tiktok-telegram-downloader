"""Общий контейнер карточки с едиными отступами и QSS-ролью."""

from PyQt6 import QtWidgets

from ui.theme import COMPACT_CARD_PADDING, CONTROL_GAP


class Card(QtWidgets.QFrame):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        margins: tuple[int, int, int, int] = (COMPACT_CARD_PADDING, 12, COMPACT_CARD_PADDING, 12),
    ):
        super().__init__(parent)
        self.setProperty("role", "card")
        self.content_layout = QtWidgets.QVBoxLayout(self)
        self.content_layout.setContentsMargins(*margins)
        self.content_layout.setSpacing(CONTROL_GAP)
