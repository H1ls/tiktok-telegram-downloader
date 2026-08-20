from __future__ import annotations

from datetime import datetime
import re

from PyQt6 import QtCore, QtWidgets

from core.updater import UpdateResult
from core.updater import update_application
from core.version import CURRENT_VERSION


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

        self.status_lbl = QtWidgets.QLabel("Status: stopped")
        self.status_lbl.setMinimumHeight(22)
        self.btn_start = QtWidgets.QPushButton("Start")
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.setEnabled(False)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.btn_start)
        top.addWidget(self.btn_stop)
        top.addStretch(1)
        top.addWidget(QtWidgets.QLabel(f"Version: {CURRENT_VERSION}"))
        top.addWidget(self.status_lbl)
        layout.addLayout(top)

        self.cb_tray = QtWidgets.QCheckBox("Minimize to tray on close")
        self.cb_tray.setChecked(True)
        layout.addWidget(self.cb_tray)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.btn_update = QtWidgets.QPushButton("Update")
        layout.addWidget(self.btn_update)

        self.btn_start.clicked.connect(self.start_clicked.emit)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_update.clicked.connect(self._do_update)

    def append_log(self, text: str) -> None:
        timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
        message = text if re.match(r"^\[[A-Z_]+\]", text) else f"[APP] {text}"
        self.log_view.appendPlainText(f"{timestamp} {message}")

    def set_running(self, running: bool) -> None:
        self.status_lbl.setText("Status: running" if running else "Status: stopped")
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
