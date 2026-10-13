from __future__ import annotations

import asyncio
import sys
from typing import Optional

from PyQt6 import QtCore, QtWidgets

from core.config import load_config
from core.service import TikTokBotService
from bot.handlers import register_handlers
from gui.main_window import MainWindow
from ui.theme import apply_theme


class ServiceThread(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    started_signal = QtCore.pyqtSignal()
    stopped_signal = QtCore.pyqtSignal()
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.svc: Optional[TikTokBotService] = None
        self._running = False

    def run(self) -> None:
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.svc = TikTokBotService(self.token, log=self.log_signal.emit, register_handlers=register_handlers)
            self.log_signal.emit("[APP] Service thread ready")
            self.loop.run_forever()
        except Exception as exc:
            self.error_signal.emit(f"[APP] Thread error: {exc}")
        finally:
            try:
                if self.loop and not self.loop.is_closed():
                    pending = [t for t in asyncio.all_tasks(self.loop) if not t.done()]
                    for task in pending:
                        task.cancel()
                    if pending:
                        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    self.loop.close()
            except Exception:
                pass
            self.log_signal.emit("[APP] Service thread stopped")

    def _submit(self, coro):
        if not self.loop:
            self.error_signal.emit("[APP] Loop not ready")
            return None
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def start_service(self) -> None:
        if not self.svc:
            self.error_signal.emit("[APP] Service not ready")
            return
        if not self.token.strip():
            self.error_signal.emit("[APP] Telegram bot token is not configured")
            return
        self.log_signal.emit("[APP] Starting bot...")
        self._submit(self.svc.start())
        self._running = True
        self.started_signal.emit()

    def stop_service(self) -> None:
        if not self.svc:
            self.error_signal.emit("[APP] Service not ready")
            return
        self.log_signal.emit("[APP] Stopping bot...")
        self._submit(self.svc.stop())
        self._running = False
        self.stopped_signal.emit()

    def update_token(self, token: str) -> None:
        self.token = token.strip()
        if self.svc and not self._running:
            self.svc.token = self.token
            self.svc.reload_config()

    def shutdown(self) -> None:
        try:
            if self.svc and self.loop:
                future = self._submit(self.svc.stop())
                if future:
                    try:
                        future.result(timeout=15)
                    except Exception as exc:
                        self.error_signal.emit(f"[APP] Shutdown stop timeout/error: {exc}")
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception as exc:
            self.error_signal.emit(f"[APP] Shutdown error: {exc}")


def main() -> None:
    cfg = load_config()

    app = QtWidgets.QApplication(sys.argv)
    apply_theme(app)
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    thread = ServiceThread(cfg.bot_token)
    thread.log_signal.connect(window.append_log)
    thread.error_signal.connect(window.append_log)
    thread.started_signal.connect(lambda: window.set_running(True))
    thread.stopped_signal.connect(lambda: window.set_running(False))

    window.start_clicked.connect(thread.start_service)
    window.stop_clicked.connect(thread.stop_service)
    window.settings_saved.connect(thread.update_token)

    thread.start()

    def on_quit() -> None:
        thread.shutdown()
        thread.quit()
        thread.wait(3000)

    app.aboutToQuit.connect(on_quit)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
