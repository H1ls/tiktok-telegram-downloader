from __future__ import annotations

from datetime import datetime
import re

from PyQt6 import QtCore, QtWidgets

from core.updater import git_update


class BotControlTab(QtWidgets.QWidget):
    start_clicked = QtCore.pyqtSignal()
    stop_clicked = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
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
        top.addWidget(self.status_lbl)
        layout.addLayout(top)

        self.cb_tray = QtWidgets.QCheckBox("Minimize to tray on close")
        self.cb_tray.setChecked(True)
        layout.addWidget(self.cb_tray)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.btn_update = QtWidgets.QPushButton("Update from Git")
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
            "Pull the latest version from the configured Git remote?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        result = git_update()
        if result.ok:
            QtWidgets.QMessageBox.information(self, "Update", result.message)
        else:
            QtWidgets.QMessageBox.warning(self, "Update", result.message)
