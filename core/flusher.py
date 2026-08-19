from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from core.files import list_media_files
from core.paths import get_user_dir


ProgressFn = Callable[[str], Awaitable[None]]


@dataclass
class FolderFlusher:
    cfg: "AppConfig"
    sender: "TelegramSender"

    async def flush_all(
        self,
        user_id: int,
        chat_id: int,
        *,
        delete_sent: bool = True,
        caption: str | None = None,
        progress: ProgressFn | None = None,
    ) -> int:
        """Send all user media files in maximum Telegram albums, then delete sent files."""
        udir = get_user_dir(self.cfg, user_id)
        files = list_media_files(udir)
        if not files:
            return 0

        sent_total = 0
        total = len(files)
        block_size = 10
        block_count = (total + block_size - 1) // block_size

        for block_index in range(block_count):
            chunk = files[block_index * block_size:(block_index + 1) * block_size]

            if progress:
                await progress(
                    f"📤 Загружаю альбом {block_index + 1}/{block_count}\n"
                    f"Файлов в альбоме: {len(chunk)}\n"
                    f"Всего: {sent_total + 1}-{sent_total + len(chunk)}/{total}"
                )

            sent = await self.sender.send_paths(
                chat_id=chat_id,
                paths=chunk,
                caption=caption if sent_total == 0 else None,
                strict_album=True,
                max_file_bytes=50 * 1024 * 1024,
                max_album_bytes=45 * 1024 * 1024,
                max_album_items=10,
            )

            sent_total += sent

            if delete_sent:
                for path in chunk[:sent]:
                    path.unlink(missing_ok=True)

            if progress:
                await progress(
                    f"✅ Альбом загружен {block_index + 1}/{block_count}\n"
                    f"Файлов: {sent}\n"
                    f"Всего отправлено: {sent_total}/{total}"
                )

        return sent_total
