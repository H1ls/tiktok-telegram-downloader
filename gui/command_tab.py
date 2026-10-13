from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from core.command_aliases import CommandValidationError
from core.command_settings_service import CommandSettingsService


class CommandTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.command_service = CommandSettingsService()
        self._build_ui()
        self._load_commands()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Handler", "Описание", "Команды"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.note = QtWidgets.QLabel("Команды указываются через запятую. Пример: start, начало, запуск")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)

        self.btn_save = QtWidgets.QPushButton("Save commands")
        layout.addWidget(self.btn_save)
        self.btn_save.clicked.connect(self.save_commands)

    def _load_commands(self) -> None:
        rows = self.command_service.load()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            key_item = QtWidgets.QTableWidgetItem(row.key)
            key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)

            title_item = QtWidgets.QTableWidgetItem(row.title)
            title_item.setFlags(title_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)

            aliases_item = QtWidgets.QTableWidgetItem(", ".join(row.aliases))

            self.table.setItem(row_index, 0, key_item)
            self.table.setItem(row_index, 1, title_item)
            self.table.setItem(row_index, 2, aliases_item)

        self.table.resizeColumnsToContents()

    def save_commands(self) -> None:
        command_aliases: dict[str, str] = {}
        for row_index in range(self.table.rowCount()):
            key_item = self.table.item(row_index, 0)
            aliases_item = self.table.item(row_index, 2)
            if not key_item:
                continue
            command_aliases[key_item.text()] = aliases_item.text() if aliases_item else ""

        try:
            self.command_service.save(command_aliases)
        except CommandValidationError as exc:
            QtWidgets.QMessageBox.warning(self, "Commands", str(exc))
            return
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Commands", f"Could not save commands:\n{exc}")
            return

        self._load_commands()
        QtWidgets.QMessageBox.information(
            self,
            "Commands",
            "Commands saved. Restart the bot to apply command handler changes.",
        )
