"""Карточка последнего download-события из существующего текстового лога."""

from pathlib import PureWindowsPath
import re

from PyQt6 import QtWidgets

from ui.theme import CARD_PADDING
from ui.widgets.card import Card
from ui.widgets.elided_label import ElidedLabel


class DownloadCard(Card):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent, margins=(CARD_PADDING, 12, CARD_PADDING, 12))
        layout = self.content_layout
        self.title = ElidedLabel("Текущая загрузка")
        self.title.setProperty("role", "downloadTitle")
        self.details = ElidedLabel("Ожидание ссылки из Telegram")
        self.details.setProperty("role", "secondary")
        self.progress = QtWidgets.QProgressBar()
        self.progress.setObjectName("downloadProgress")
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        layout.addWidget(self.title)
        layout.addWidget(self.details)
        layout.addWidget(self.progress)
        self.setToolTip("Последнее событие загрузки. Прогресс параллельных задач поступает в общий лог.")

    def consume_log(self, text: str) -> None:
        if not text.startswith("[DOWNLOAD] "):
            return
        message = text.removeprefix("[DOWNLOAD] ").strip()
        self.title.set_full_text("Текущая загрузка · последнее событие")
        self.progress.setRange(0, 0)
        if message.startswith("Finished: "):
            self.title.set_full_text(PureWindowsPath(message.removeprefix("Finished: ")).name)
            self.details.set_full_text("Загрузка завершена")
            self.progress.setRange(0, 1000)
            self.progress.setValue(1000)
        elif message.startswith("Failed: "):
            self.details.set_full_text(message)
            self.progress.setRange(0, 1000)
            self.progress.setValue(0)
        elif message.startswith("Started: "):
            self.details.set_full_text("Подготовка загрузки…")
        elif message.startswith("download ") and not message.startswith("download finished:"):
            details = message.removeprefix("download ")
            percent = re.search(r"(\d+(?:\.\d+)?)%", details)
            if percent:
                self.progress.setRange(0, 1000)
                self.progress.setValue(round(min(100.0, float(percent.group(1))) * 10))
            details = re.sub(r"eta (\d+)s", r"Осталось \1 с", details)
            details = details.replace("eta ?s", "Оставшееся время неизвестно")
            details = re.sub(r", (\d+)s$", r", Прошло \1 с", details)
            self.details.set_full_text(f"Скачивание… {details}")
        else:
            self.details.set_full_text(message)
