"""Переиспользуемая строка пути; выбор и сохранение принадлежат странице."""

from PyQt6 import QtCore, QtWidgets

from ui.theme import icon


class FolderRow(QtWidgets.QWidget):
    def __init__(self, title: str, path: str, *, read_only: bool = False, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        label = QtWidgets.QLabel(title)
        label.setMinimumWidth(148)
        self.edit = QtWidgets.QLineEdit(path)
        self.edit.setReadOnly(read_only)
        self.edit.setMinimumWidth(0)
        self.edit.setAccessibleName(title)
        label.setBuddy(self.edit)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.browse_button.setIcon(icon("folder"))
        self.browse_button.setIconSize(QtCore.QSize(20, 20))
        self.browse_button.setAccessibleName(f"Выбрать папку: {title}")
        layout.addWidget(label)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.browse_button)
