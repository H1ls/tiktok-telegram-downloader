from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from PyQt6 import QtCore, QtWidgets

from gui.bot_control_tab import BotControlTab
from ui.theme import apply_theme


class BotUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        apply_theme(cls.app)

    def setUp(self) -> None:
        self.widget = BotControlTab()
        self.widget.resize(730, 367)
        self.widget.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.widget.close()

    def test_start_stop_and_tray_contract(self) -> None:
        received = []
        self.widget.start_clicked.connect(lambda: received.append("start"))
        self.widget.stop_clicked.connect(lambda: received.append("stop"))
        self.widget.btn_start.click()
        self.widget.set_running(True)
        self.assertEqual(self.widget.status_lbl.text(), "Running")
        self.assertFalse(self.widget.btn_start.isEnabled())
        self.widget.btn_stop.click()
        self.widget.set_running(False)
        self.assertEqual(received, ["start", "stop"])
        self.assertFalse(self.widget.btn_stop.isEnabled())
        self.assertTrue(self.widget.minimize_to_tray_enabled())
        self.widget.cb_tray.setChecked(False)
        self.assertFalse(self.widget.minimize_to_tray_enabled())

    def test_progress_formats_do_not_confuse_elapsed_and_eta(self) -> None:
        card = self.widget.download_card
        self.widget.append_log("[DOWNLOAD] download 94.6% (0.6/0.6 MB), 0.58 MB/s, 1s")
        self.assertEqual(card.progress.value(), 946)
        self.assertIn("Прошло 1 с", card.details.toolTip())
        self.assertNotIn("Осталось", card.details.toolTip())
        self.widget.append_log("[DOWNLOAD] download 94.6% (0.6/0.6 MB), 0.58 MB/s, eta 1s")
        self.assertIn("Осталось 1 с", card.details.toolTip())

    def test_unknown_total_does_not_retain_old_percentage(self) -> None:
        card = self.widget.download_card
        self.widget.append_log("[DOWNLOAD] download 50.0% (1.0/2.0 MB), 0.20 MB/s, eta 5s")
        self.widget.append_log("[DOWNLOAD] download 1.5 MB, 0.20 MB/s, eta ?s")
        self.assertEqual(card.progress.maximum(), 0)
        self.assertIn("1.5 MB", card.details.toolTip())
        self.assertIn("Оставшееся время неизвестно", card.details.toolTip())

    def test_completion_filename_does_not_leak_into_unidentified_progress(self) -> None:
        card = self.widget.download_card
        self.widget.append_log(r"[DOWNLOAD] Finished: D:\TikTok\123\video.mp4")
        self.assertEqual(card.title.toolTip(), "video.mp4")
        self.assertEqual(card.progress.value(), 1000)
        self.widget.append_log("[DOWNLOAD] download 20.0% (1.0/5.0 MB), 1.00 MB/s, eta 4s")
        self.assertNotIn("video.mp4", card.title.toolTip())
        self.widget.append_log("[DOWNLOAD] Failed: user=123, error=RuntimeError: failure")
        self.assertEqual(card.progress.value(), 0)
        self.widget.append_log("[DOWNLOAD] yt_dlp: started")
        self.assertEqual(card.progress.maximum(), 0)

    def test_unrelated_log_does_not_change_download(self) -> None:
        card = self.widget.download_card
        self.widget.append_log("[DOWNLOAD] download 10.0%")
        self.widget.append_log("[UPDATE] 100%")
        self.assertEqual(card.progress.value(), 100)

    def test_auto_scroll_can_be_paused_even_at_bottom(self) -> None:
        for index in range(100):
            self.widget.append_log(f"[APP] line {index}")
        self.app.processEvents()
        scrollbar = self.widget.log_view.verticalScrollBar()
        self.assertEqual(scrollbar.value(), scrollbar.maximum())
        self.widget.cb_auto_scroll.setChecked(False)
        for position in (0, scrollbar.maximum()):
            scrollbar.setValue(position)
            self.widget.append_log("[APP] another line")
            self.app.processEvents()
            self.assertEqual(scrollbar.value(), position)
        self.widget.cb_auto_scroll.setChecked(True)
        self.assertEqual(scrollbar.value(), scrollbar.maximum())

    def test_clear_only_changes_visual_log_and_copy_uses_full_text(self) -> None:
        self.widget.append_log("[DOWNLOAD] download 50.0%")
        text = self.widget.log_view.toPlainText()
        clipboard = Mock()
        with patch.object(QtWidgets.QApplication, "clipboard", return_value=clipboard):
            self.widget.btn_copy_logs.click()
        clipboard.setText.assert_called_once_with(text)
        self.widget.btn_clear_logs.click()
        self.assertEqual(self.widget.log_view.toPlainText(), "")
        self.assertEqual(self.widget.download_card.progress.value(), 500)

    def test_long_log_and_filename_do_not_expand_page(self) -> None:
        size = self.widget.size()
        self.widget.append_log("[APP] " + "x" * 5000)
        self.widget.append_log("[DOWNLOAD] Finished: D:/TikTok/" + "x" * 1000 + ".mp4")
        self.app.processEvents()
        self.assertEqual(self.widget.size(), size)
        self.assertIn("…", self.widget.download_card.title.text())
        for card in (self.widget.controls_card, self.widget.logs_card, self.widget.download_card):
            self.assertTrue(self.widget.rect().contains(card.geometry()))
            for child in card.findChildren(QtWidgets.QWidget, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly):
                self.assertTrue(card.rect().contains(child.geometry()), type(child).__name__)


if __name__ == "__main__":
    unittest.main()
