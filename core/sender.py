from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import (TelegramRetryAfter, TelegramNetworkError, TelegramBadRequest, TelegramEntityTooLarge, )
from aiogram.types import InputMediaPhoto, InputMediaVideo
from aiogram.types.input_file import FSInputFile

from core.config import AppConfig


@dataclass
class TelegramSender:
    bot: Bot

    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}

    def _is_image(self, path: Path) -> bool:
        return path.suffix.lower() in self.IMAGE_EXTS

    def _is_video(self, path: Path) -> bool:
        return path.suffix.lower() in self.VIDEO_EXTS

    def _validate_paths(self, paths: list[Path], max_file_bytes: int) -> None:
        for p in paths:
            if not p.exists() or not p.is_file():
                raise FileNotFoundError(f"Файл не найден: {p}")

            size = p.stat().st_size
            if size <= 0:
                raise ValueError(f"Пустой файл: {p}")

            if size > max_file_bytes:
                mb = size / (1024 * 1024)
                limit_mb = max_file_bytes / (1024 * 1024)
                raise ValueError(
                    f"Файл слишком большой: {p.name} ({mb:.1f} MB) > лимита {limit_mb:.0f} MB")

    def _chunk_paths(self, paths: list[Path], *, max_items: int, max_album_bytes: int, ) -> list[list[Path]]:
        chunks: list[list[Path]] = []
        current: list[Path] = []
        current_bytes = 0

        for p in paths:
            size = p.stat().st_size

            need_split = (current and (len(current) >= max_items or current_bytes + size > max_album_bytes))

            if need_split:
                chunks.append(current)
                current = []
                current_bytes = 0

            current.append(p)
            current_bytes += size

        if current:
            chunks.append(current)

        return chunks

    async def _send_single(self, chat_id: int, path: Path, caption: str | None = None, *, retries: int = 3, ) -> int:
        last_exc: Exception | None = None
        delivery_uncertain = False

        for _ in range(retries):
            try:
                f = FSInputFile(str(path))

                if self._is_image(path):
                    await self.bot.send_photo(chat_id=chat_id, photo=f, caption=caption)
                else:
                    await self.bot.send_video(chat_id=chat_id, video=f, caption=caption)

                return 1

            except TelegramEntityTooLarge as e:
                last_exc = e
                break
            except TelegramRetryAfter as e:
                last_exc = e
                await asyncio.sleep(float(e.retry_after) + 0.2)
            except TelegramNetworkError as e:
                # Sending media is not idempotent: Telegram may deliver the
                # message while the client only sees a broken response. Do not
                # retry automatically, otherwise the same file can be posted
                # several times before the caller deletes it.
                last_exc = e
                delivery_uncertain = True
                break
            except TelegramBadRequest as e:
                last_exc = e
                break

        if delivery_uncertain:
            raise RuntimeError(f"Single send result is uncertain: {last_exc}") from last_exc

        # fallback на document
        try:
            f = FSInputFile(str(path))
            await self.bot.send_document(chat_id=chat_id, document=f, caption=caption)
            return 1
        except Exception as e:
            if last_exc is None:
                last_exc = e
            raise RuntimeError(f"Single send failed: {last_exc}") from last_exc

    async def _send_album_once(self, chat_id: int, paths: list[Path], caption: str | None = None, *,
                               retries: int = 3, ) -> int:
        media = []
        for i, p in enumerate(paths[:10]):
            f = FSInputFile(str(p))
            cap = caption if i == 0 else None

            if self._is_image(p):
                media.append(InputMediaPhoto(media=f, caption=cap))
            else:
                media.append(InputMediaVideo(media=f, caption=cap))

        last_exc: Exception | None = None
        delivery_uncertain = False

        for _ in range(retries):
            try:
                await self.bot.send_media_group(chat_id=chat_id, media=media)
                return len(media)
            except TelegramEntityTooLarge as e:
                raise e
            except TelegramRetryAfter as e:
                last_exc = e
                await asyncio.sleep(float(e.retry_after) + 0.2)
            except (TelegramNetworkError, TelegramBadRequest) as e:
                # See _send_single: after a send request reaches Telegram, a
                # network error does not prove the album was not posted.
                last_exc = e
                delivery_uncertain = isinstance(e, TelegramNetworkError)
                break

        if delivery_uncertain:
            raise RuntimeError(f"Album send result is uncertain: {last_exc}") from last_exc

        raise RuntimeError(f"Album send failed after {retries} retries: {last_exc}") from last_exc

    async def _send_recursive(self, chat_id: int, paths: list[Path], caption: str | None = None, *,
                              retries: int = 3, ) -> int:
        if not paths:
            return 0

        if len(paths) == 1:
            return await self._send_single(chat_id=chat_id,
                                           path=paths[0],
                                           caption=caption,
                                           retries=retries)

        try:
            return await self._send_album_once(chat_id=chat_id,
                                               paths=paths,
                                               caption=caption,
                                               retries=retries)
        except TelegramEntityTooLarge:
            mid = len(paths) // 2
            sent_left = await self._send_recursive(chat_id=chat_id, paths=paths[:mid],
                                                   caption=caption, retries=retries)
            sent_right = await self._send_recursive(chat_id=chat_id, paths=paths[mid:],
                                                    caption=None,
                                                    retries=retries)
            return sent_left + sent_right

    async def send_paths(
            self,
            chat_id: int,
            paths: list[Path],
            caption: str | None = None,
            *,
            strict_album: bool = False,
            retries: int = 3,
            max_bytes: int | None = None,
            max_file_bytes: int = AppConfig.MAX_FILE_SIZE_BYTES,
            max_album_bytes: int = AppConfig.MAX_ALBUM_SIZE_BYTES,
            max_album_items: int = AppConfig.MAX_ALBUM_ITEMS, ) -> int:

        if max_bytes is not None:
            max_file_bytes = max_bytes

        if not paths:
            return 0

        self._validate_paths(paths, max_file_bytes=max_file_bytes)

        chunks = self._chunk_paths(paths,
                                   max_items=max_album_items,
                                   max_album_bytes=max_album_bytes, )

        total_sent = 0

        for i, chunk in enumerate(chunks):
            chunk_caption = caption if i == 0 else None
            try:
                total_sent += await self._send_recursive(chat_id=chat_id,
                                                         paths=chunk,
                                                         caption=chunk_caption,
                                                         retries=retries, )
            except Exception:
                if strict_album:
                    raise
                raise

        return total_sent
