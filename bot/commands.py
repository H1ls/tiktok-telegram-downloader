from __future__ import annotations

from aiogram import Dispatcher, types
from aiogram.filters import Command

from bot.messages import format_mode, settings_text, start_text
from core.command_aliases import aliases_for
from core.config import save_config


def register_command_handlers(dp: Dispatcher, svc) -> None:
    def ucfg(user_id: int) -> dict:
        return svc._user_cfg(user_id)

    def aliases(command_key: str) -> list[str]:
        return aliases_for(svc.cfg.command_aliases, command_key)

    @dp.message(Command(*aliases("start")))
    async def start(message: types.Message) -> None:
        await message.answer(start_text())

    @dp.message(Command(*aliases("my")))
    async def cmd_my(message: types.Message) -> None:
        user_id = int(message.from_user.id)
        await message.answer(settings_text(user_id, ucfg(user_id), svc.pending_count(user_id)))

    @dp.message(Command(*aliases("bind")))
    async def cmd_bind(message: types.Message) -> None:
        if message.chat.type not in ("group", "supergroup"):
            await message.answer("Команда /bind работает в группе. В ЛС используй: /bind_id -100...")
            return

        user_cfg = ucfg(message.from_user.id)
        user_cfg["target_chat_id"] = int(message.chat.id)
        user_cfg["delivery_mode"] = "group_batch"
        save_config(svc.cfg)
        await message.answer("Группа привязана. Ссылки будут копиться и уходить пачкой сюда.")

    @dp.message(Command(*aliases("bind_id")))
    async def cmd_bind_id(message: types.Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) != 2:
            await message.answer("Используй: /bind_id -1003115579453")
            return

        try:
            group_id = int(parts[1].strip())
        except ValueError:
            await message.answer("Неверный ID. Пример: /bind_id -1003115579453")
            return

        user_cfg = ucfg(message.from_user.id)
        user_cfg["target_chat_id"] = group_id
        user_cfg["delivery_mode"] = "group_batch"
        save_config(svc.cfg)
        await message.answer(f"Привязал target_chat_id = {group_id}\nРежим: group_batch.")

    @dp.message(Command(*aliases("route")))
    async def cmd_route(message: types.Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) != 2:
            await message.answer("Используй: /route dm или /route group")
            return

        arg = parts[1].strip().lower()
        if arg not in ("dm", "group", "group_batch"):
            await message.answer("Используй: /route dm или /route group")
            return

        user_cfg = ucfg(message.from_user.id)
        user_cfg["delivery_mode"] = "dm" if arg == "dm" else "group_batch"
        save_config(svc.cfg)
        await message.answer(f"mode = {format_mode(user_cfg['delivery_mode'])}")

    @dp.message(Command(*aliases("batch")))
    async def cmd_batch(message: types.Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Используй: /batch 1..10")
            return

        value = max(1, min(10, int(parts[1])))
        user_cfg = ucfg(message.from_user.id)
        user_cfg["batch_size"] = value
        save_config(svc.cfg)
        await message.answer(f"batch_size = {value}")

    @dp.message(Command(*aliases("keep")))
    async def cmd_keep(message: types.Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Используй: /keep 1..1000")
            return

        value = max(1, min(1000, int(parts[1])))
        user_cfg = ucfg(message.from_user.id)
        user_cfg["queue_keep_max"] = value
        save_config(svc.cfg)
        await message.answer(f"queue_keep_max = {value}")

    @dp.message(Command(*aliases("quality")))
    async def cmd_quality(message: types.Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Используй: /quality 360|480|720|1080")
            return

        quality = int(parts[1])
        if quality not in (360, 480, 720, 1080):
            await message.answer("Только: 360, 480, 720, 1080")
            return

        user_cfg = ucfg(message.from_user.id)
        user_cfg["max_height"] = quality
        save_config(svc.cfg)
        await message.answer(f"max_height = {quality}p")

    @dp.message(Command(*aliases("status")))
    async def cmd_status(message: types.Message) -> None:
        user_id = int(message.from_user.id)
        user_cfg = ucfg(user_id)
        batch_size = min(10, int(user_cfg.get("batch_size") or 1))
        await message.answer(f"В очереди: {svc.pending_count(user_id)} файлов. Порог пачки: {batch_size}.")

    @dp.message(Command(*aliases("flush")))
    async def cmd_flush(message: types.Message) -> None:
        user_id = int(message.from_user.id)
        user_cfg = ucfg(user_id)
        mode = (user_cfg.get("delivery_mode") or "dm").lower()
        target_chat_id = int(message.chat.id)

        if mode == "group_batch":
            bound_chat_id = user_cfg.get("target_chat_id")
            if not bound_chat_id:
                await message.answer("Группа не привязана. В группе: /bind или в ЛС: /bind_id -100...")
                return
            target_chat_id = int(bound_chat_id)

        await svc.flush_user(user_id, target_chat_id=target_chat_id, notify_chat_id=int(message.chat.id))

    @dp.message(Command(*aliases("last")))
    async def cmd_last(message: types.Message) -> None:
        if message.chat.type not in ("group", "supergroup"):
            await message.answer("/last работает в группе.")
            return

        user_id = int(message.from_user.id)
        user_cfg = ucfg(user_id)
        bound_chat_id = user_cfg.get("target_chat_id")
        if int(message.chat.id) != int(bound_chat_id or 0):
            await message.answer("Эта группа не привязана к тебе. Напиши /bind в нужной группе.")
            return

        await svc.flush_user(user_id, target_chat_id=int(message.chat.id), notify_chat_id=int(message.chat.id))

    @dp.message(Command(*aliases("id")))
    async def my_id(message: types.Message) -> None:
        await message.answer(f"user_id={message.from_user.id}")
