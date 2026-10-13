from __future__ import annotations

import unittest
from unittest.mock import patch

from PyQt6 import QtCore, QtGui, QtWidgets

from core.command_aliases import COMMAND_TITLES, DEFAULT_COMMAND_ALIASES
from core.command_settings_service import CommandAliasRow
from core.settings_service import SettingsSnapshot
from core.version import CURRENT_VERSION
from gui.main_window import MainWindow
from ui.theme import apply_theme
from ui.widgets.card import Card
from ui.widgets.elided_label import ElidedLabel


class MainWindowUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        apply_theme(cls.app)

    def setUp(self) -> None:
        rows = [CommandAliasRow(key, COMMAND_TITLES[key], aliases) for key, aliases in DEFAULT_COMMAND_ALIASES.items()]
        snapshot = SettingsSnapshot("fixture-token", "D:/TikTok", "D:/TikTok", False)
        with patch("gui.settings_tab.SettingsService.load", return_value=snapshot), patch("gui.command_tab.CommandSettingsService.load", return_value=rows):
            self.window = MainWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.tray.tray.hide()
        self.window._really_quit = True
        self.window.close()

    def test_navigation_and_geometry_at_four_required_sizes(self) -> None:
        window = self.window
        for width, height in ((820, 580), (900, 620), (1000, 700), (1200, 800)):
            window.resize(width, height)
            for index, button in enumerate(window.nav_buttons):
                button.click()
                self.app.processEvents()
                self.assertEqual(window.pages.currentIndex(), index)
                self.assertEqual([b.isChecked() for b in window.nav_buttons], [i == index for i in range(3)])
                page = window.pages.currentWidget()
                self.assertLessEqual(page.minimumSizeHint().height(), page.height())
                for card in page.findChildren(Card):
                    self.assertTrue(page.rect().contains(card.geometry()))
                    for child in card.findChildren(QtWidgets.QWidget, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly):
                        self.assertTrue(card.rect().contains(child.geometry()))
                for label in window.findChildren(QtWidgets.QLabel):
                    if label.isVisible() and label.text() and not label.wordWrap() and not isinstance(label, ElidedLabel):
                        self.assertLessEqual(label.fontMetrics().horizontalAdvance(label.text()), label.contentsRect().width())
                self.assertEqual(window.command_tab.table.horizontalScrollBar().maximum(), 0)
            children = (window.app_icon, window.title_label, window.version_badge, window.status_badge)
            self.assertTrue(all(window.header.rect().contains(c.geometry()) for c in children))
            self.assertTrue(all(not a.geometry().intersects(b.geometry()) for a, b in zip(children, children[1:])))

    def test_status_and_signal_contract_across_pages(self) -> None:
        window = self.window
        received = []
        window.start_clicked.connect(lambda: received.append("start"))
        window.stop_clicked.connect(lambda: received.append("stop"))
        window.settings_saved.connect(received.append)
        window.bot_tab.btn_start.click()
        window.nav_buttons[1].click()
        window.set_running(True)
        self.assertEqual(window.status_badge.property("status"), "running")
        self.assertEqual(window.bot_tab.status_lbl.text(), "Running")
        window.bot_tab.btn_stop.click()
        window.set_running(False)
        window.settings_tab.settings_saved.emit("fixture-token")
        window.append_log("[DOWNLOAD] download 94.6%")
        self.assertEqual(window.bot_tab.download_card.progress.value(), 946)
        self.assertEqual(window.version_badge.text(), f"v{CURRENT_VERSION}")
        self.assertEqual(received, ["start", "stop", "fixture-token"])

    def test_tray_and_all_close_branches(self) -> None:
        window = self.window
        self.assertFalse(window.tray.tray.icon().isNull())
        window.tray._hide()
        self.assertFalse(window.isVisible())
        window.tray._show()
        self.assertTrue(window.isVisible())
        window.tray._on_activated(QtWidgets.QSystemTrayIcon.ActivationReason.Trigger)
        self.assertFalse(window.isVisible())
        with patch.object(window.tray.tray, "showMessage"):
            event = QtGui.QCloseEvent()
            window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.assertTrue(window.tray.tray.isVisible())
        window.bot_tab.cb_tray.setChecked(False)
        stopped = []
        window.stop_clicked.connect(lambda: stopped.append(True))
        with patch.object(QtWidgets.QApplication, "quit") as quit_app:
            window.closeEvent(QtGui.QCloseEvent())
            quit_app.assert_called_once()
        self.assertEqual(stopped, [True])
        self.assertFalse(window.tray.tray.isVisible())
        window._really_quit = True
        event = QtGui.QCloseEvent()
        window.closeEvent(event)
        self.assertTrue(event.isAccepted())


if __name__ == "__main__":
    unittest.main()
