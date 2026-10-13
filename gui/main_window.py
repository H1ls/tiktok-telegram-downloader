from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from gui.bot_control_tab import BotControlTab
from gui.command_tab import CommandTab
from gui.settings_tab import SettingsTab
from gui.tray import Tray
from core.version import CURRENT_VERSION
from ui.theme import CARD_PADDING, CONTROL_GAP, PAGE_MARGIN, icon
from ui.widgets.status_badge import StatusBadge


class MainWindow(QtWidgets.QMainWindow):
    start_clicked = QtCore.pyqtSignal()
    stop_clicked = QtCore.pyqtSignal()
    settings_saved = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok Downloader Bot")
        self.setWindowIcon(icon("app"))

        self._build_ui()

        self.bot_tab.start_clicked.connect(self.start_clicked.emit)
        self.bot_tab.stop_clicked.connect(self.stop_clicked.emit)
        self.settings_tab.settings_saved.connect(self.settings_saved.emit)

        self.tray = Tray(self)
        self.tray.tray.hide()
        self.setMinimumSize(820, 580)
        self.resize(980, 680)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        central.setObjectName("appShell")
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        layout.setSpacing(16)

        self._build_header()
        layout.addWidget(self.header)

        page_container = self._build_pages()
        layout.addWidget(self.navigation)
        layout.addWidget(page_container, 1)

    def _build_header(self) -> None:
        self.header = QtWidgets.QFrame()
        self.header.setObjectName("appHeader")
        header_layout = QtWidgets.QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        self.app_icon = QtWidgets.QLabel()
        self.app_icon.setPixmap(icon("app").pixmap(40, 40))
        header_layout.addWidget(self.app_icon)
        self.title_label = QtWidgets.QLabel("TikTok Downloader Bot")
        self.title_label.setProperty("role", "appTitle")
        header_layout.addWidget(self.title_label)
        self.version_badge = QtWidgets.QLabel(f"v{CURRENT_VERSION}")
        self.version_badge.setProperty("role", "badge")
        self.version_badge.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        header_layout.addWidget(self.version_badge)
        header_layout.addStretch(1)
        self.status_badge = StatusBadge()
        header_layout.addWidget(self.status_badge)

    def _build_pages(self) -> QtWidgets.QFrame:
        self.navigation = QtWidgets.QFrame()
        self.navigation.setObjectName("navigation")
        navigation_layout = QtWidgets.QHBoxLayout(self.navigation)
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.setSpacing(CONTROL_GAP)
        self.navigation_group = QtWidgets.QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        self.nav_buttons: list[QtWidgets.QPushButton] = []

        page_container = QtWidgets.QFrame()
        page_container.setProperty("role", "container")
        page_layout = QtWidgets.QVBoxLayout(page_container)
        page_layout.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        page_layout.setSpacing(0)
        self.pages = QtWidgets.QStackedWidget()
        self.pages.setObjectName("pages")
        # Сохраняем доступ к count/currentIndex/setCurrentIndex через прежнее имя.
        self.tabs = self.pages
        page_layout.addWidget(self.pages)

        self.bot_tab = BotControlTab()
        self.settings_tab = SettingsTab()
        self.command_tab = CommandTab()
        for index, (page, title, icon_name) in enumerate((
            (self.bot_tab, "Bot", "bot"),
            (self.settings_tab, "Settings", "settings"),
            (self.command_tab, "Command", "commands"),
        )):
            page.layout().setContentsMargins(0, 0, 0, 0)
            page.layout().setSpacing(16)
            self.pages.addWidget(page)
            button = QtWidgets.QPushButton(title)
            button.setProperty("role", "navigation")
            button.setIcon(icon(icon_name))
            button.setIconSize(QtCore.QSize(24, 24))
            button.setCheckable(True)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.navigation_group.addButton(button, index)
            self.nav_buttons.append(button)
            navigation_layout.addWidget(button)
        navigation_layout.addStretch(1)
        self.navigation_group.idClicked.connect(self.pages.setCurrentIndex)
        self.pages.currentChanged.connect(self._sync_navigation)
        self._sync_navigation(self.pages.currentIndex())
        return page_container

    def append_log(self, text: str) -> None:
        self.bot_tab.append_log(text)

    def set_running(self, running: bool) -> None:
        self.bot_tab.set_running(running)
        self.status_badge.set_running(running)

    def _sync_navigation(self, index: int) -> None:
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)

    def closeEvent(self, event) -> None:
        if getattr(self, "_really_quit", False):
            self.tray.tray.hide()
            event.accept()
            return

        if self.bot_tab.minimize_to_tray_enabled():
            event.ignore()
            self.hide()
            if not self.tray.tray.isVisible():
                self.tray.tray.show()
            self.tray.tray.showMessage("TikTok Bot", "Application minimized to tray")
            return

        event.ignore()
        self.stop_clicked.emit()
        self.tray.tray.hide()
        QtWidgets.QApplication.quit()
