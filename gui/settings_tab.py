from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from core.settings_service import SettingsService, SettingsSnapshot
from ui.theme import icon
from ui.widgets.card import Card
from ui.widgets.folder_row import FolderRow
from ui.widgets.toggle_switch import ToggleSwitch


class SettingsTab(QtWidgets.QWidget):
    settings_saved = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.settings_service = SettingsService()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        settings = self.settings_service.load()

        self._build_autostart_card(settings)
        layout.addWidget(self.autostart_card)

        self._build_telegram_card(settings)
        layout.addWidget(self.telegram_card)

        self._build_folders_card(settings)
        layout.addWidget(self.folders_card)

        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(12)
        self.saved_label = self._label("", "secondary")
        self.saved_label.setObjectName("settingsSaved")
        footer.addWidget(self.saved_label)
        footer.addStretch(1)
        self.btn_save_settings = QtWidgets.QPushButton("Save settings")
        self.btn_save_settings.setProperty("variant", "primary")
        self.btn_save_settings.setIcon(icon("save"))
        self.btn_save_settings.setFixedSize(200, 42)
        footer.addWidget(self.btn_save_settings)
        layout.addLayout(footer)
        layout.addStretch(1)
        self.saved_timer = QtCore.QTimer(self)
        self.saved_timer.setSingleShot(True)
        self.saved_timer.setInterval(1800)
        self.saved_timer.timeout.connect(self.saved_label.clear)

        self.btn_data_dir.clicked.connect(lambda: self._choose_dir(self.data_dir_edit))
        self.btn_download_dir.clicked.connect(lambda: self._choose_dir(self.download_dir_edit))
        self.btn_save_settings.clicked.connect(self.save_settings)

    def _build_autostart_card(self, settings: SettingsSnapshot) -> None:
        self.autostart_card = Card()
        autostart_layout = self.autostart_card.content_layout
        autostart_row = QtWidgets.QHBoxLayout()
        autostart_row.setSpacing(12)
        autostart_description = QtWidgets.QVBoxLayout()
        autostart_description.setSpacing(4)
        autostart_description.addWidget(self._label("Автозапуск", "sectionTitle"))
        autostart_description.addWidget(self._label("Запускать приложение вместе с Windows", "secondary"))
        autostart_row.addLayout(autostart_description, 1)
        self.btn_autostart = ToggleSwitch()
        self.btn_autostart.setChecked(settings.autostart)
        self.btn_autostart.toggled.connect(self._sync_autostart_button)
        self._sync_autostart_button(self.btn_autostart.isChecked())
        autostart_row.addWidget(self.btn_autostart)
        autostart_layout.addLayout(autostart_row)

    def _build_telegram_card(self, settings: SettingsSnapshot) -> None:
        self.telegram_card = Card()
        telegram_layout = self.telegram_card.content_layout
        telegram_row = QtWidgets.QHBoxLayout()
        telegram_row.setSpacing(12)
        telegram_description = QtWidgets.QVBoxLayout()
        telegram_description.setSpacing(4)
        telegram_description.addWidget(self._label("Telegram", "sectionTitle"))
        telegram_description.addWidget(self._label("Токен вашего бота", "secondary"))
        telegram_row.addLayout(telegram_description)
        self.token_edit = QtWidgets.QLineEdit(settings.bot_token)
        self.token_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("Telegram bot token")
        self.token_edit.setAccessibleName("Telegram bot token")
        self.token_edit.setMinimumWidth(0)
        telegram_row.addWidget(self.token_edit, 1)
        self.btn_token_visibility = QtWidgets.QToolButton()
        self.btn_token_visibility.setCheckable(True)
        self.btn_token_visibility.setIconSize(QtCore.QSize(20, 20))
        self.btn_token_visibility.toggled.connect(self._set_token_visible)
        self._set_token_visible(False)
        telegram_row.addWidget(self.btn_token_visibility)
        telegram_layout.addLayout(telegram_row)

    def _build_folders_card(self, settings: SettingsSnapshot) -> None:
        self.folders_card = Card()
        folders_layout = self.folders_card.content_layout
        self.settings_folder_row = FolderRow("Settings folder", settings.data_dir, read_only=True)
        self.download_folder_row = FolderRow("Temp/video folder", settings.download_root)
        self.data_dir_edit = self.settings_folder_row.edit
        self.download_dir_edit = self.download_folder_row.edit
        self.btn_data_dir = self.settings_folder_row.browse_button
        self.btn_download_dir = self.download_folder_row.browse_button
        folders_layout.addWidget(self.settings_folder_row)
        folders_layout.addWidget(self.download_folder_row)
        folder_note = self._label("При сохранении настройки переносятся в выбранную папку загрузок", "secondary")
        folder_note.setWordWrap(True)
        folders_layout.addWidget(folder_note)

    @staticmethod
    def _label(text: str, role: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setProperty("role", role)
        return label

    def _set_token_visible(self, visible: bool) -> None:
        mode = QtWidgets.QLineEdit.EchoMode.Normal if visible else QtWidgets.QLineEdit.EchoMode.Password
        self.token_edit.setEchoMode(mode)
        self.btn_token_visibility.setIcon(icon("eye_off" if visible else "eye"))
        text = "Скрыть токен" if visible else "Показать токен"
        self.btn_token_visibility.setToolTip(text)
        self.btn_token_visibility.setAccessibleName(text)

    def save_settings(self) -> None:
        self.saved_timer.stop()
        self.saved_label.clear()
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
        self.saved_label.setText("✓ Saved")
        self.saved_timer.start()

    def _apply_snapshot(self, settings: SettingsSnapshot) -> None:
        self.token_edit.setText(settings.bot_token)
        self.btn_token_visibility.setChecked(False)
        self._set_token_visible(False)
        self.data_dir_edit.setText(settings.data_dir)
        self.download_dir_edit.setText(settings.download_root)
        self.btn_autostart.setChecked(settings.autostart)

    def _choose_dir(self, target: QtWidgets.QLineEdit) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder", target.text())
        if path:
            # SettingsService сохраняет оба пути в выбранной папке загрузок.
            self.data_dir_edit.setText(path)
            self.download_dir_edit.setText(path)

    def _sync_autostart_button(self, enabled: bool) -> None:
        self.btn_autostart.setAccessibleName("Автозапуск с Windows")
        self.btn_autostart.setAccessibleDescription("Включён" if enabled else "Выключен")
        state = "Включён" if enabled else "Выключен"
        self.btn_autostart.setToolTip(f"{state} — применится после сохранения")
