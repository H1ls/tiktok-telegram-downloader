from __future__ import annotations

from datetime import datetime
import re

from PyQt6 import QtCore, QtWidgets

from core.updater import UpdateResult
from core.updater import update_application
from core.version import CURRENT_VERSION
from ui.theme import CARD_PADDING, icon
from ui.widgets.card import Card
from ui.widgets.download_card import DownloadCard


class UpdateThread(QtCore.QThread):
    progress_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal(object)

    def run(self) -> None:
        result = update_application(progress=self.progress_signal.emit)
        self.finished_signal.emit(result)


class BotControlTab(QtWidgets.QWidget):
    start_clicked = QtCore.pyqtSignal()
    stop_clicked = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self._update_thread: UpdateThread | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self._build_controls_card()
        self._build_logs_card()
        self.download_card = DownloadCard()
        layout.addWidget(self.controls_card)
        layout.addWidget(self.logs_card, 1)
        layout.addWidget(self.download_card)

        self.btn_start.clicked.connect(self.start_clicked.emit)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_update.clicked.connect(self._do_update)
        self.btn_clear_logs.clicked.connect(self.log_view.clear)
        self.btn_copy_logs.clicked.connect(self._copy_logs)
        self.cb_auto_scroll.toggled.connect(self._auto_scroll_changed)

    def _build_controls_card(self) -> None:
        self.controls_card = Card(margins=(CARD_PADDING, 12, CARD_PADDING, 12))
        controls = self.controls_card.content_layout
        self.btn_start = QtWidgets.QPushButton("Start")
        self.btn_start.setProperty("variant", "primary")
        self.btn_start.setIcon(icon("play"))
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.setIcon(icon("stop"))
        self.btn_stop.setEnabled(False)
        for button in (self.btn_start, self.btn_stop):
            button.setMinimumWidth(112)
            button.setIconSize(QtCore.QSize(20, 20))

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self.btn_start)
        top.addWidget(self.btn_stop)
        self.btn_update = QtWidgets.QPushButton("Update")
        top.addWidget(self.btn_update)
        top.addStretch(1)
        self.status_lbl = QtWidgets.QLabel("Stopped")
        self.status_lbl.setProperty("status", "stopped")
        for title, value in (("Status", self.status_lbl), ("Version", QtWidgets.QLabel(CURRENT_VERSION))):
            info = QtWidgets.QVBoxLayout()
            info.setSpacing(4)
            caption = QtWidgets.QLabel(title)
            caption.setProperty("role", "secondary")
            value.setProperty("role", "infoValue")
            info.addWidget(caption)
            info.addWidget(value)
            top.addLayout(info)
        controls.addLayout(top)

        self.cb_tray = QtWidgets.QCheckBox("Minimize to tray on close")
        self.cb_tray.setChecked(True)
        controls.addWidget(self.cb_tray)
        tray_note = QtWidgets.QLabel("Приложение будет свернуто в системный трей при закрытии окна")
        tray_note.setProperty("role", "secondary")
        tray_note.setWordWrap(True)
        controls.addWidget(tray_note)

    def _build_logs_card(self) -> None:
        self.logs_card = Card()
        logs = self.logs_card.content_layout
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(8)
        logs_icon = QtWidgets.QLabel()
        logs_icon.setPixmap(icon("logs").pixmap(24, 24))
        toolbar.addWidget(logs_icon)
        logs_title = QtWidgets.QLabel("Logs")
        logs_title.setProperty("role", "sectionTitle")
        toolbar.addWidget(logs_title)
        toolbar.addStretch(1)
        self.btn_clear_logs = QtWidgets.QPushButton("Clear")
        self.btn_clear_logs.setIcon(icon("trash"))
        self.btn_copy_logs = QtWidgets.QPushButton("Copy")
        self.btn_copy_logs.setIcon(icon("copy"))
        self.cb_auto_scroll = QtWidgets.QCheckBox("Auto-scroll")
        self.cb_auto_scroll.setChecked(True)
        toolbar.addWidget(self.btn_clear_logs)
        toolbar.addWidget(self.btn_copy_logs)
        toolbar.addWidget(self.cb_auto_scroll)
        logs.addLayout(toolbar)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setObjectName("botLogs")
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setMinimumHeight(56)
        logs.addWidget(self.log_view, 1)

    def _copy_logs(self) -> None:
        QtWidgets.QApplication.clipboard().setText(self.log_view.toPlainText())

    def _auto_scroll_changed(self, enabled: bool) -> None:
        if enabled:
            scrollbar = self.log_view.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def append_log(self, text: str) -> None:
        timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
        message = text if re.match(r"^\[[A-Z_]+\]", text) else f"[APP] {text}"
        vertical = self.log_view.verticalScrollBar()
        horizontal = self.log_view.horizontalScrollBar()
        scroll_position = (vertical.value(), horizontal.value())
        self.log_view.appendPlainText(f"{timestamp} {message}")
        if self.cb_auto_scroll.isChecked():
            vertical.setValue(vertical.maximum())
        else:
            vertical.setValue(scroll_position[0])
            horizontal.setValue(scroll_position[1])
        self.download_card.consume_log(text)

    def set_running(self, running: bool) -> None:
        self.status_lbl.setText("Running" if running else "Stopped")
        self.status_lbl.setProperty("status", "running" if running else "stopped")
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)
        self.status_lbl.update()
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def minimize_to_tray_enabled(self) -> bool:
        return self.cb_tray.isChecked()

    def _do_update(self) -> None:
        reply = QtWidgets.QMessageBox.question(
            self,
            "Update",
            "Check for updates and install the latest available version?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self.btn_update.setEnabled(False)
        self.append_log("[UPDATE] Started")
        self._update_thread = UpdateThread()
        self._update_thread.progress_signal.connect(self.append_log)
        self._update_thread.finished_signal.connect(self._update_finished)
        self._update_thread.finished.connect(self._update_thread.deleteLater)
        self._update_thread.start()

    def _update_finished(self, result: UpdateResult) -> None:
        self.btn_update.setEnabled(True)
        self._update_thread = None
        if result.ok:
            self.append_log(f"[UPDATE] {result.message}")
            QtWidgets.QMessageBox.information(self, "Update", result.message)
            if result.should_exit:
                QtWidgets.QApplication.quit()
        else:
            self.append_log(f"[UPDATE] Failed: {result.message}")
            QtWidgets.QMessageBox.warning(self, "Update", result.message)
