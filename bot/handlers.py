from __future__ import annotations

from aiogram import Dispatcher

from bot.commands import register_command_handlers
from bot.link_handler import register_link_handlers


def register_handlers(dp: Dispatcher, svc) -> None:
    register_command_handlers(dp, svc)
    register_link_handlers(dp, svc)
