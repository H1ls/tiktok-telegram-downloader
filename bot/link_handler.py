from __future__ import annotations

import asyncio
import re

from aiogram import Dispatcher, F, types

from core.downloader import expand_url, extract_tiktok_url, is_tiktok_photo
from core.jobs import Job


def register_link_handlers(dp: Dispatcher, svc) -> None:
    @dp.message(F.text)
    async def on_text(message: types.Message) -> None:
        text = message.text or ""
        if text.startswith("/"):
            return

        url = extract_tiktok_url(text)
        if not url:
            return

        expanded = await asyncio.to_thread(expand_url, url)
        if is_tiktok_photo(expanded):
            await message.reply("Это TikTok фото-карусель. Скачивание не поддерживается.")
            return

        job = Job(
            chat_id=int(message.chat.id),
            user_id=int(message.from_user.id),
            url=expanded,
            msg_id=message.message_id,
            source_url=url,
            target_chat_id=int(message.chat.id) if _wants_current_chat(text, url) else None,
        )
        position = svc.enqueue(job)
        await message.reply(f"Принял. В очереди #{position}\n{url}")


def _wants_current_chat(text: str, url: str) -> bool:
    tail = text.replace(url, " ")
    return re.search(r"(^|\s)(me|мне)(\s|$)", tail, flags=re.IGNORECASE) is not None
