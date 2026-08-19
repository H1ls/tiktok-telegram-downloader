from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from core.settings_service import SettingsService, SettingsSnapshot


class SettingsTab(QtWidgets.QWidget):
    settings_saved = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.settings_service = SettingsService()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)
        settings = self.settings_service.load()

        self.btn_autostart = QtWidgets.QPushButton()
        self.btn_autostart.setCheckable(True)
        self.btn_autostart.setChecked(settings.autostart)
        self.btn_autostart.toggled.connect(self._sync_autostart_button)
        self._sync_autostart_button(self.btn_autostart.isChecked())
        layout.addRow("Autostart", self.btn_autostart)

        self.token_edit = QtWidgets.QLineEdit(settings.bot_token)
        self.token_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("Telegram bot token")
        layout.addRow("TG token", self.token_edit)

        self.data_dir_edit = QtWidgets.QLineEdit(settings.data_dir)
        self.btn_data_dir = QtWidgets.QPushButton("Browse")
        data_row = QtWidgets.QHBoxLayout()
        data_row.addWidget(self.data_dir_edit)
        data_row.addWidget(self.btn_data_dir)
        layout.addRow("Settings folder", data_row)

        self.download_dir_edit = QtWidgets.QLineEdit(settings.download_root)
        self.btn_download_dir = QtWidgets.QPushButton("Browse")
        download_row = QtWidgets.QHBoxLayout()
        download_row.addWidget(self.download_dir_edit)
        download_row.addWidget(self.btn_download_dir)
        layout.addRow("Temp/video folder", download_row)

        self.btn_save_settings = QtWidgets.QPushButton("Save settings")
        layout.addRow("", self.btn_save_settings)

        self.btn_data_dir.clicked.connect(lambda: self._choose_dir(self.data_dir_edit))
        self.btn_download_dir.clicked.connect(lambda: self._choose_dir(self.download_dir_edit))
        self.btn_save_settings.clicked.connect(self.save_settings)

    def save_settings(self) -> None:
        try:
            settings = self.settings_service.save(
                bot_token=self.token_edit.text(),
                data_dir=self.data_dir_edit.text().strip(),
                download_root=self.download_dir_edit.text(),
                autostart_enabled=self.btn_autostart.isChecked(),
            )
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Settings", f"Could not save settings:\n{exc}")
            return

        self._apply_snapshot(settings)
        self.settings_saved.emit(settings.bot_token)
        QtWidgets.QMessageBox.information(self, "Settings", "Settings saved.")

    def _apply_snapshot(self, settings: SettingsSnapshot) -> None:
        self.token_edit.setText(settings.bot_token)
        self.data_dir_edit.setText(settings.data_dir)
        self.download_dir_edit.setText(settings.download_root)
        self.btn_autostart.setChecked(settings.autostart)

    def _choose_dir(self, target: QtWidgets.QLineEdit) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder", target.text())
        if path:
            target.setText(path)

    def _sync_autostart_button(self, enabled: bool) -> None:
        self.btn_autostart.setText("Выкл автозапуск с Windows" if enabled else "Вкл автозапуск с Windows")
