from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PyQt6 import QtCore, QtTest, QtWidgets

from core.config import AppConfig
from core.settings_service import SettingsSnapshot
from gui.settings_tab import SettingsTab
from ui.theme import apply_theme


class SettingsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        apply_theme(cls.app)

    def setUp(self) -> None:
        self.snapshot = SettingsSnapshot("fixture-token", "D:/TikTok", "D:/TikTok", True)
        with patch("gui.settings_tab.SettingsService.load", return_value=self.snapshot):
            self.widget = SettingsTab()
        self.widget.resize(730, 367)
        self.widget.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.widget.close()

    def test_loaded_switch_and_keyboard_toggle(self) -> None:
        self.assertTrue(self.widget.btn_autostart.isChecked())
        self.widget.btn_autostart.setFocus()
        QtTest.QTest.keyClick(self.widget.btn_autostart, QtCore.Qt.Key.Key_Space)
        self.assertFalse(self.widget.btn_autostart.isChecked())
        self.widget.btn_autostart.click()
        self.assertTrue(self.widget.btn_autostart.isChecked())

    def test_token_visibility_and_snapshot_remasking(self) -> None:
        edit = self.widget.token_edit
        self.assertEqual(edit.text(), self.snapshot.bot_token)
        self.assertEqual(edit.echoMode(), QtWidgets.QLineEdit.EchoMode.Password)
        self.widget.btn_token_visibility.click()
        self.assertEqual(edit.echoMode(), QtWidgets.QLineEdit.EchoMode.Normal)
        self.widget._apply_snapshot(self.snapshot)
        self.assertEqual(edit.echoMode(), QtWidgets.QLineEdit.EchoMode.Password)
        self.assertFalse(self.widget.btn_token_visibility.isChecked())

    def test_both_browse_buttons_preserve_coupled_paths_and_cancel(self) -> None:
        self.assertTrue(self.widget.data_dir_edit.isReadOnly())
        for button in (self.widget.btn_data_dir, self.widget.btn_download_dir):
            with patch.object(QtWidgets.QFileDialog, "getExistingDirectory", return_value="D:/Chosen"):
                button.click()
            self.assertEqual(self.widget.data_dir_edit.text(), "D:/Chosen")
            self.assertEqual(self.widget.download_dir_edit.text(), "D:/Chosen")
            with patch.object(QtWidgets.QFileDialog, "getExistingDirectory", return_value=""):
                button.click()
            self.assertEqual(self.widget.download_dir_edit.text(), "D:/Chosen")

    def test_save_emits_snapshot_and_inline_feedback_without_success_dialog(self) -> None:
        received = []
        self.widget.settings_saved.connect(received.append)
        save = Mock(return_value=self.snapshot)
        with patch.object(self.widget.settings_service, "save", save), patch.object(QtWidgets.QMessageBox, "information") as dialog:
            self.widget.btn_save_settings.click()
        save.assert_called_once_with(bot_token="fixture-token", data_dir="D:/TikTok", download_root="D:/TikTok", autostart_enabled=True)
        self.assertEqual(received, [self.snapshot.bot_token])
        self.assertEqual(self.widget.saved_label.text(), "✓ Saved")
        self.assertTrue(self.widget.saved_timer.isActive())
        dialog.assert_not_called()
        # Проверяем настоящее истечение таймера с коротким интервалом.
        self.widget.saved_timer.start(10)
        QtTest.QTest.qWait(30)
        self.assertEqual(self.widget.saved_label.text(), "")

    def test_failure_does_not_emit_success(self) -> None:
        received = []
        self.widget.settings_saved.connect(received.append)
        with patch.object(self.widget.settings_service, "save", side_effect=OSError("fixture failure")), patch.object(QtWidgets.QMessageBox, "warning") as warning:
            self.widget.btn_save_settings.click()
        warning.assert_called_once()
        self.assertEqual(received, [])
        self.assertEqual(self.widget.saved_label.text(), "")
        self.assertFalse(self.widget.saved_timer.isActive())

    def test_settings_fit_minimum_page_with_long_paths(self) -> None:
        self.widget.download_dir_edit.setText("D:/" + "long-path/" * 100)
        self.app.processEvents()
        self.assertLessEqual(self.widget.minimumSizeHint().height(), 367)
        for card in (self.widget.autostart_card, self.widget.telegram_card, self.widget.folders_card):
            self.assertTrue(self.widget.rect().contains(card.geometry()))
            for child in card.findChildren(QtWidgets.QWidget, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly):
                self.assertTrue(card.rect().contains(child.geometry()))
        self.assertTrue(self.widget.rect().contains(self.widget.btn_save_settings.geometry()))

    def test_real_json_save_and_new_page_reload_in_isolated_directory(self) -> None:
        # Настоящие config/settings функции, но только временные файлы и mock реестра.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "downloads"
            registry_state = {"enabled": False}

            def set_enabled(enabled):
                registry_state["enabled"] = enabled

            with patch("core.config.app_dir", return_value=root), patch("core.config._default_data_dir", return_value=root), patch.dict(os.environ, {"DOWNLOAD_ROOT": ""}), patch("core.autostart.is_enabled", side_effect=lambda: registry_state["enabled"]), patch("core.autostart.set_enabled", side_effect=set_enabled) as registry_save:
                before_keys = set(asdict(AppConfig()))
                page = SettingsTab()
                page.token_edit.setText("  persisted-fixture-token  ")
                page.download_dir_edit.setText(str(target))
                page.btn_autostart.setChecked(True)
                registry_save.assert_not_called()
                page.save_settings()
                registry_save.assert_called_once_with(True)
                saved = json.loads((target / "config.json").read_text(encoding="utf-8"))
                self.assertEqual(set(saved), before_keys)
                self.assertEqual(saved["bot_token"], "persisted-fixture-token")
                self.assertTrue(saved["autostart"])
                self.assertEqual(json.loads((root / "storage.json").read_text(encoding="utf-8"))["data_dir"], str(target.resolve()))
                page.close()
                registry_state["enabled"] = False
                reloaded = SettingsTab()
                self.assertEqual(reloaded.token_edit.text(), "persisted-fixture-token")
                self.assertEqual(reloaded.data_dir_edit.text(), str(target.resolve()))
                self.assertEqual(reloaded.download_dir_edit.text(), str(target.resolve()))
                self.assertTrue(reloaded.btn_autostart.isChecked())
                reloaded.close()


if __name__ == "__main__":
    unittest.main()
